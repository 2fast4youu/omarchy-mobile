package org.omamobile.pixelcontrol;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothSocket;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.InputFilter;
import android.text.InputType;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final UUID SERVICE = UUID.fromString("8a1e65d9-812b-4c53-8936-e8ea3f67050f");
    private static final int INK = 0xff11192b;
    private static final int MUTED = 0xff51627b;
    private static final int BLUE = 0xff2b4fa5;
    private static final int CONNECTED = 0xff166b56;
    private static final int PERMISSION = 1;
    private static final int HISTORY_LIMIT = 48_000;
    private final ExecutorService reader = Executors.newSingleThreadExecutor();
    private final ExecutorService writer = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final StringBuilder pending = new StringBuilder();
    private final StringBuilder history = new StringBuilder();
    private boolean outputScheduled;
    private int pendingGeneration;
    private int escapeState;

    private TextView state;
    private Button connection;
    private Button send;
    private Button interrupt;
    private TextView terminal;
    private ScrollView outputScroll;
    private EditText input;
    private volatile BluetoothSocket socket;
    private volatile int generation;
    private boolean connecting;
    private boolean ready;

    @Override public void onCreate(Bundle savedState) {
        super.onCreate(savedState);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(0xfff8fbff);
        page.setPadding(dp(18), dp(14), dp(18), dp(12));
        if (Build.VERSION.SDK_INT >= 30) {
            page.setOnApplyWindowInsetsListener((view, insets) -> {
                var bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                var keyboard = insets.getInsets(WindowInsets.Type.ime());
                view.setPadding(dp(18) + bars.left, dp(14) + bars.top, dp(18) + bars.right,
                        dp(12) + Math.max(bars.bottom, keyboard.bottom));
                return insets;
            });
        }
        setContentView(page);
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController bars = getWindow().getInsetsController();
            int darkIcons = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                    | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
            if (bars != null) bars.setSystemBarsAppearance(darkIcons, darkIcons);
        }

        TextView title = new TextView(this);
        title.setText("Pixel-Konsole");
        title.setTextSize(27);
        title.setTextColor(INK);
        title.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        page.addView(title);
        state = new TextView(this);
        state.setText("Wähle dein gekoppeltes Pixel.");
        state.setTextSize(14);
        state.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        page.addView(state);
        connection = button("Pixel auswählen", true);
        page.addView(connection);
        connection.setOnClickListener(view -> {
            if (ready || connecting) stop("Verbindung getrennt.");
            else choosePixel();
        });

        outputScroll = new ScrollView(this);
        outputScroll.setFillViewport(true);
        outputScroll.setBackgroundColor(INK);
        LinearLayout.LayoutParams outputParams = new LinearLayout.LayoutParams(-1, 0, 1);
        outputParams.topMargin = dp(8);
        page.addView(outputScroll, outputParams);
        terminal = new TextView(this);
        terminal.setTypeface(Typeface.MONOSPACE);
        terminal.setTextSize(13);
        terminal.setTextColor(0xffe4edff);
        terminal.setPadding(dp(12), dp(9), dp(12), dp(9));
        terminal.setTextIsSelectable(true);
        terminal.setText("Die Ausgabe vom Pixel erscheint hier.");
        outputScroll.addView(terminal);

        input = new EditText(this);
        input.setSingleLine(true);
        input.setTextColor(INK);
        input.setHintTextColor(MUTED);
        input.setHint("Befehl für das Pixel");
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        input.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(4096)});
        input.setImeOptions(EditorInfo.IME_ACTION_SEND);
        input.setOnEditorActionListener((view, action, event) -> {
            if (action != EditorInfo.IME_ACTION_SEND) return false;
            sendLine();
            return true;
        });
        page.addView(input);

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        page.addView(buttons);
        send = button("Senden", true);
        send.setOnClickListener(view -> sendLine());
        buttons.addView(send, new LinearLayout.LayoutParams(0, -2, 1));
        interrupt = button("Strg+C", false);
        interrupt.setContentDescription("Laufenden Befehl abbrechen");
        interrupt.setOnClickListener(view -> transmit(new byte[]{3}));
        buttons.addView(interrupt);
        render();
    }

    private void choosePixel() {
        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.BLUETOOTH_CONNECT}, PERMISSION);
            return;
        }
        BluetoothManager manager = getSystemService(BluetoothManager.class);
        BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
        if (adapter == null) {
            state.setText("Bluetooth ist auf diesem Handy nicht verfügbar.");
            return;
        }
        if (!adapter.isEnabled()) {
            state.setText("Schalte Bluetooth auf diesem Handy ein.");
            openSettings();
            return;
        }
        List<BluetoothDevice> devices = new ArrayList<>(adapter.getBondedDevices());
        if (devices.isEmpty()) {
            state.setText("Kopple das Pixel in den Bluetooth-Einstellungen.");
            openSettings();
            return;
        }
        String[] names = devices.stream().map(this::deviceName).toArray(String[]::new);
        new AlertDialog.Builder(this).setTitle("Gekoppeltes Pixel auswählen")
                .setItems(names, (dialog, which) -> connect(devices.get(which)))
                .setNeutralButton("Bluetooth-Einstellungen", (dialog, button) -> openSettings())
                .setNegativeButton("Abbrechen", null).show();
    }

    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(request, permissions, results);
        if (request != PERMISSION) return;
        if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) choosePixel();
        else state.setText("Erlaube in den App-Einstellungen den Zugriff auf Geräte in der Nähe.");
    }

    private String deviceName(BluetoothDevice device) {
        String name = device.getName();
        return name == null || name.trim().isEmpty() ? device.getAddress() : name;
    }

    private void connect(BluetoothDevice device) {
        String name = deviceName(device);
        int current = ++generation;
        connecting = true;
        synchronized (pending) {
            pending.setLength(0);
            pendingGeneration = current;
        }
        history.setLength(0);
        escapeState = 0;
        terminal.setText("");
        state.setText("Verbinde mit " + name + " …");
        render();
        Runnable expiry = () -> {
            if (generation == current && connecting) stop("Die Bluetooth-Verbindung hat zu lange gedauert.");
        };
        main.postDelayed(expiry, 20_000);
        reader.execute(() -> openSession(device, name, current, expiry));
    }

    private synchronized boolean register(BluetoothSocket candidate, int current) {
        if (generation != current) return false;
        socket = candidate;
        return true;
    }

    private void openSession(BluetoothDevice device, String name, int current, Runnable expiry) {
        boolean opened = false;
        try (BluetoothSocket candidate = device.createRfcommSocketToServiceRecord(SERVICE)) {
            if (!register(candidate, current)) return;
            candidate.connect();
            candidate.getOutputStream().write("{\"action\":\"terminal\"}\n".getBytes(StandardCharsets.UTF_8));
            candidate.getOutputStream().flush();
            InputStream stream = candidate.getInputStream();
            JSONObject reply = new JSONObject(readReply(stream));
            if (!reply.optBoolean("ok")) throw new IOException("Terminal unavailable");
            opened = true;
            main.post(() -> {
                if (generation != current) return;
                main.removeCallbacks(expiry);
                connecting = false;
                ready = true;
                state.setText("Verbunden mit " + name);
                render();
                input.requestFocus();
            });
            InputStreamReader text = new InputStreamReader(stream, StandardCharsets.UTF_8);
            char[] buffer = new char[4096];
            int length;
            while ((length = text.read(buffer)) != -1 && generation == current) {
                queueOutput(buffer, length, current);
            }
        } catch (IOException | JSONException | SecurityException failure) {
            // The paired device can refuse access or the link can close while the terminal is open.
        } finally {
            String message = opened ? "Die Pixelsitzung wurde beendet."
                    : "Verbindung fehlgeschlagen. Prüfe die Freigabe am Pixel.";
            main.post(() -> {
                main.removeCallbacks(expiry);
                if (generation == current) stop(message);
            });
        }
    }

    private static String readReply(InputStream stream) throws IOException {
        ByteArrayOutputStream reply = new ByteArrayOutputStream();
        for (int i = 0; i < 4096; i++) {
            int value = stream.read();
            if (value == '\n') return new String(reply.toByteArray(), StandardCharsets.UTF_8);
            if (value < 0) break;
            reply.write(value);
        }
        throw new IOException("No terminal reply");
    }

    private void sendLine() {
        if (!ready) return;
        String command = input.getText().toString() + "\n";
        transmit(command.getBytes(StandardCharsets.UTF_8));
        input.setText("");
    }

    private void transmit(byte[] message) {
        BluetoothSocket current = socket;
        if (!ready || current == null) return;
        writer.execute(() -> {
            try {
                current.getOutputStream().write(message);
                current.getOutputStream().flush();
            } catch (IOException failure) {
                main.post(() -> {
                    if (socket == current) stop("Die Bluetooth-Verbindung wurde getrennt.");
                });
            }
        });
    }

    private void queueOutput(char[] bytes, int length, int current) {
        synchronized (pending) {
            if (generation != current) return;
            pendingGeneration = current;
            pending.append(bytes, 0, length);
            if (pending.length() > HISTORY_LIMIT) pending.delete(0, pending.length() - HISTORY_LIMIT);
            if (outputScheduled) return;
            outputScheduled = true;
        }
        main.post(() -> {
            String text;
            int owner;
            synchronized (pending) {
                text = pending.toString();
                owner = pendingGeneration;
                pending.setLength(0);
                outputScheduled = false;
            }
            if (owner == generation) appendOutput(text);
        });
    }

    private void appendOutput(String text) {
        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            switch (escapeState) {
                case 1: escapeState = ch == '[' ? 2 : ch == ']' ? 3 : 0; break;
                case 2: if (ch >= '@' && ch <= '~') escapeState = 0; break;
                case 3: if (ch == '\u0007') escapeState = 0; else if (ch == '\u001b') escapeState = 4; break;
                case 4: escapeState = ch == '\\' ? 0 : 3; break;
                default:
                    if (ch == '\u001b') escapeState = 1;
                    else if (ch == '\n' || ch == '\t' || !Character.isISOControl(ch)) history.append(ch);
            }
        }
        if (history.length() > HISTORY_LIMIT) history.delete(0, history.length() - HISTORY_LIMIT);
        terminal.setText(history);
        outputScroll.post(() -> outputScroll.scrollTo(0, terminal.getHeight()));
    }

    private synchronized void stop(String message) {
        generation++;
        BluetoothSocket previous = socket;
        socket = null;
        if (previous != null) {
            try { previous.close(); } catch (IOException ignored) { }
        }
        connecting = false;
        ready = false;
        state.setText(message);
        render();
    }

    private void render() {
        connection.setText(connecting ? "Verbindung abbrechen" : ready ? "Verbindung trennen" : "Pixel auswählen");
        state.setTextColor(ready ? CONNECTED : MUTED);
        input.setEnabled(ready);
        send.setEnabled(ready);
        interrupt.setEnabled(ready);
    }

    private void openSettings() { startActivity(new Intent(Settings.ACTION_BLUETOOTH_SETTINGS)); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private Button button(String label, boolean primary) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setMinimumHeight(dp(48));
        if (primary) {
            int[][] enabled = {new int[]{-android.R.attr.state_enabled}, new int[0]};
            button.setBackgroundTintList(new ColorStateList(enabled, new int[]{0xffe3ebf7, BLUE}));
            button.setTextColor(new ColorStateList(enabled, new int[]{MUTED, 0xffffffff}));
        }
        return button;
    }

    @Override protected void onDestroy() {
        stop("Verbindung getrennt.");
        reader.shutdownNow();
        writer.shutdownNow();
        main.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}
