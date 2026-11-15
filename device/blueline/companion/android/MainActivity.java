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
import android.graphics.Typeface;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
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
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final List<Button> actions = new ArrayList<>();

    private LinearLayout page;
    private TextView state;
    private Button connection;
    private Button lamp;
    private EditText prompt;
    private volatile BluetoothSocket socket;
    private BufferedReader input;
    private boolean ready;
    private boolean busy;
    private boolean lampOn;
    private String peerName;

    @Override public void onCreate(Bundle savedState) {
        super.onCreate(savedState);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(0xffffffff);
        page.setPadding(dp(22), dp(20), dp(22), dp(20));
        if (Build.VERSION.SDK_INT >= 30) {
            page.setOnApplyWindowInsetsListener((view, insets) -> {
                var bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                view.setPadding(dp(22) + bars.left, dp(20) + bars.top,
                        dp(22) + bars.right, dp(20) + bars.bottom);
                return insets;
            });
        }
        scroll.addView(page);
        setContentView(scroll);

        label("Pixel-Steuerung", 28, INK, true, 0);
        state = label("Wähle dein gekoppeltes Pixel 3.", 15, MUTED, false, 7);
        state.setAccessibilityLiveRegion(TextView.ACCESSIBILITY_LIVE_REGION_POLITE);
        connection = button("Pixel auswählen", true, 8);
        connection.setOnClickListener(view -> {
            if (ready) {
                disconnect();
                message("Verbindung getrennt.");
            } else {
                choosePixel();
            }
        });

        label("Geräteaktionen", 18, INK, true, 24);
        lamp = actionButton("Taschenlampe einschalten", 6);
        lamp.setOnClickListener(view -> send(object("action", "torch", "enabled", !lampOn)));
        actionButton("Kamera öffnen", 3).setOnClickListener(view -> send(object("action", "open", "app", "camera")));
        actionButton("Dateien öffnen", 3).setOnClickListener(view -> send(object("action", "open", "app", "files")));

        label("Hermes", 18, INK, true, 23);
        prompt = new EditText(this);
        prompt.setHint("Auftrag für Hermes auf dem Pixel");
        prompt.setTextColor(INK);
        prompt.setHintTextColor(MUTED);
        prompt.setTextSize(16);
        prompt.setMinLines(2);
        prompt.setMaxLines(4);
        prompt.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        prompt.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(1500)});
        add(prompt, 6);
        actionButton("Auftrag ans Pixel senden", 6).setOnClickListener(view -> {
            String text = prompt.getText().toString().trim();
            if (text.isEmpty()) {
                prompt.setError("Gib einen Auftrag ein.");
                return;
            }
            send(object("action", "hermes", "prompt", text));
        });
        render();
    }

    private void choosePixel() {
        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.BLUETOOTH_CONNECT}, PERMISSION);
            return;
        }
        BluetoothAdapter adapter = getSystemService(BluetoothManager.class).getAdapter();
        if (adapter == null) {
            message("Dieses Handy hat keinen Bluetooth-Adapter.");
            return;
        }
        if (!adapter.isEnabled()) {
            bluetoothSettings("Schalte Bluetooth auf diesem Handy ein.");
            return;
        }
        List<BluetoothDevice> devices = new ArrayList<>(adapter.getBondedDevices());
        if (devices.isEmpty()) {
            bluetoothSettings("Kopple das Pixel 3 in den Bluetooth-Einstellungen.");
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
        if (request == PERMISSION && results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
            choosePixel();
        } else if (request == PERMISSION) {
            message("Erlaube in den App-Einstellungen den Zugriff auf Geräte in der Nähe.");
        }
    }

    private String deviceName(BluetoothDevice device) {
        String name = device.getName();
        return name == null || name.trim().isEmpty() ? device.getAddress() : name;
    }

    private void connect(BluetoothDevice device) {
        peerName = deviceName(device);
        message("Verbinde mit " + peerName + " …");
        operate(() -> {
            BluetoothSocket newSocket = device.createRfcommSocketToServiceRecord(SERVICE);
            socket = newSocket;
            newSocket.connect();
            input = new BufferedReader(new InputStreamReader(newSocket.getInputStream(), StandardCharsets.UTF_8));
            return exchange(object("action", "status", null, null));
        }, true);
    }

    private void send(JSONObject request) {
        if (!ready || busy) return;
        message("Sende ans Pixel …");
        operate(() -> exchange(request), false);
    }

    private JSONObject exchange(JSONObject request) throws IOException, JSONException {
        BluetoothSocket connection = socket;
        if (connection == null) throw new IOException("No Bluetooth connection");
        connection.getOutputStream().write((request + "\n").getBytes(StandardCharsets.UTF_8));
        connection.getOutputStream().flush();
        String line = input.readLine();
        if (line == null) throw new IOException("Bluetooth connection closed");
        return new JSONObject(line);
    }

    private void operate(Exchange work, boolean connecting) {
        busy = true;
        render();
        Runnable abort = this::closeSocket;
        main.postDelayed(abort, 20_000);
        worker.execute(() -> {
            try {
                JSONObject reply = work.run();
                main.post(() -> {
                    main.removeCallbacks(abort);
                    if (isDestroyed()) return;
                    busy = false;
                    ready = !connecting || reply.optBoolean("ok");
                    if (!ready) closeSocket();
                    lampOn = reply.optBoolean("torch", lampOn);
                    String result = reply.has("torch") && !connecting
                            ? (lampOn ? "Taschenlampe ist an." : "Taschenlampe ist aus.")
                            : "Verbunden mit " + peerName;
                    message(reply.optBoolean("ok") ? reply.optString("message", result)
                            : reply.optString("error", "Das Pixel hat die Aktion abgelehnt."));
                    render();
                });
            } catch (IOException | JSONException | SecurityException failure) {
                closeSocket();
                main.post(() -> {
                    main.removeCallbacks(abort);
                    if (isDestroyed()) return;
                    busy = false;
                    ready = false;
                    message(connecting ? "Verbindung fehlgeschlagen. Gib dieses Handy am Pixel frei."
                            : "Bluetooth-Verbindung verloren. Wähle das Pixel erneut.");
                    render();
                });
            }
        });
    }

    private void closeSocket() {
        BluetoothSocket old = socket;
        socket = null;
        if (old != null) {
            try { old.close(); } catch (IOException ignored) { }
        }
    }

    private void disconnect() {
        closeSocket();
        ready = false;
        render();
    }

    private void render() {
        connection.setText(ready ? "Verbindung trennen" : "Pixel auswählen");
        connection.setEnabled(!busy);
        lamp.setText(lampOn ? "Taschenlampe ausschalten" : "Taschenlampe einschalten");
        for (Button button : actions) button.setEnabled(ready && !busy);
        state.setTextColor(ready ? CONNECTED : MUTED);
    }

    private void message(String text) { state.setText(text); }
    private void openSettings() { startActivity(new Intent(Settings.ACTION_BLUETOOTH_SETTINGS)); }
    private void bluetoothSettings(String text) { message(text); openSettings(); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private TextView label(String text, int size, int color, boolean bold, int margin) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);
        if (bold) view.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        add(view, margin);
        return view;
    }

    private Button button(String text, boolean primary, int margin) {
        Button button = new Button(this);
        button.setText(text);
        button.setAllCaps(false);
        button.setMinimumHeight(dp(48));
        if (primary) {
            button.setBackgroundTintList(android.content.res.ColorStateList.valueOf(BLUE));
            button.setTextColor(0xffffffff);
        }
        add(button, margin);
        return button;
    }

    private Button actionButton(String text, int margin) {
        Button button = button(text, false, margin);
        actions.add(button);
        return button;
    }

    private void add(android.view.View view, int margin) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.topMargin = dp(margin);
        page.addView(view, params);
    }

    private static JSONObject object(String key, Object value, String secondKey, Object secondValue) {
        try {
            JSONObject result = new JSONObject().put(key, value);
            if (secondKey != null) result.put(secondKey, secondValue);
            return result;
        } catch (JSONException impossible) {
            throw new IllegalArgumentException(impossible);
        }
    }

    @Override protected void onDestroy() {
        closeSocket();
        worker.shutdownNow();
        main.removeCallbacksAndMessages(null);
        super.onDestroy();
    }

    private interface Exchange { JSONObject run() throws IOException, JSONException; }
}
