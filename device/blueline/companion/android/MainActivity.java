package org.omamobile.pixelcontrol;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothSocket;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.InputFilter;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Pixel-Konsole: steuert das Pixel 3 mit Omarchy Mobile ueber das
 * authentifizierte RFCOMM-Terminal von blueline-bluetooth-control.
 *
 * Agent-Auftraege und Schnellaktionen laufen in derselben Shell. Jede wird
 * zwischen zwei Markierungen (0x1E 'S' ... 0x1E 'E' Rueckgabewert) gesetzt,
 * so landet ihre Ausgabe in einer eigenen Sprechblase statt im Konsolenstrom.
 */
public final class MainActivity extends Activity {
    private static final UUID SERVICE = UUID.fromString("8a1e65d9-812b-4c53-8936-e8ea3f67050f");
    private static final int BG = 0xff0f1420;
    private static final int SURFACE = 0xff182031;
    private static final int SURFACE_HIGH = 0xff222c42;
    private static final int TEXT = 0xffe8eefc;
    private static final int MUTED = 0xff8a97b2;
    private static final int ACCENT = 0xff7aa2ff;
    private static final int ACCENT_DARK = 0xff2b4fa5;
    private static final int OK = 0xff4cc38a;
    private static final int WARN = 0xffe0a84f;
    private static final int ERROR = 0xffef6f6f;
    private static final int PERMISSION = 1;
    private static final int HISTORY_LIMIT = 48_000;
    private static final char MARK = '\u001e';
    private static final String[] PROVIDERS = {"Automatisch", "Antigravity", "Offline"};
    private static final String[] ROUTES = {"auto", "api", "offline"};
    private static final String[][] SLASH = {
        {"/hilfe", "Alle Befehle"},
        {"/neu", "Neues Gespräch beginnen"},
        {"/gespraeche", "Gespräche anzeigen und wechseln"},
        {"/name", "Aktuelles Gespräch benennen"},
        {"/modell", "auto, api oder offline"},
        {"/status", "Akku, Energie, Netz, Speicher"},
        {"/akku", "Ladestand und Temperatur"},
        {"/wlan", "Netz, Signal und IP"},
        {"/agenten", "Welche Modelle erreichbar sind"},
        {"/licht", "Taschenlampe ein/aus"},
        {"/bildschirm", "Bildschirm einschalten"},
        {"/hell", "Helligkeit 0–100"},
        {"/laut", "Lautstärke 0–100"},
        {"/sperren", "Pixel sperren"},
        {"/sh", "Shell-Befehl als Karte"},
        {"/stopp", "Laufenden Auftrag abbrechen"},
    };
    private static final String[] PROVIDER_HINTS = {
        "Mac per USB, sonst deine API", "Deine API im Internet", "Kleines Modell am Pixel"};

    private final ExecutorService reader = Executors.newSingleThreadExecutor();
    private final ExecutorService writer = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final StringBuilder pending = new StringBuilder();
    private final StringBuilder console = new StringBuilder();
    private final List<TextView> providerChips = new ArrayList<>();
    private final List<View> needsConnection = new ArrayList<>();
    private final Map<String, String[]> actions = new LinkedHashMap<>();
    private LinearLayout slashRow;
    private HorizontalScrollView slashScroll;
    private String sessionId;
    private boolean listing;
    private final List<String[]> sessions = new ArrayList<>();
    private boolean outputScheduled;
    private int pendingGeneration;

    // Parser-Zustand fuer den Ausgabestrom
    private int escapeState;
    private int markState;          // 0 normal, 1 nach MARK, 2 in Markierungszeile
    private char markKind;
    private final StringBuilder markLine = new StringBuilder();
    private boolean inBlock;
    private StringBuilder blockText;
    private TextView blockView;
    private TextView blockMeta;

    private SharedPreferences prefs;
    private TextView state;
    private View stateDot;
    private Button connection;
    private Button send;
    private Button stopButton;
    private TextView tabAgent;
    private TextView tabConsole;
    private View agentPane;
    private View consolePane;
    private LinearLayout chat;
    private ScrollView chatScroll;
    private TextView terminal;
    private ScrollView outputScroll;
    private EditText input;
    private volatile BluetoothSocket socket;
    private volatile int generation;
    private boolean connecting;
    private boolean ready;
    private boolean agentTab = true;
    private int provider;
    private int running;

    @Override public void onCreate(Bundle savedState) {
        super.onCreate(savedState);
        prefs = getSharedPreferences("pixel", MODE_PRIVATE);
        provider = Math.max(0, Math.min(PROVIDERS.length - 1, prefs.getInt("provider", 0)));
        sessionId = prefs.getString("session", null);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(BG);
        page.setPadding(dp(16), dp(12), dp(16), dp(10));
        if (Build.VERSION.SDK_INT >= 30) {
            page.setOnApplyWindowInsetsListener((view, insets) -> {
                var bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                var keyboard = insets.getInsets(WindowInsets.Type.ime());
                view.setPadding(dp(16) + bars.left, dp(12) + bars.top, dp(16) + bars.right,
                        dp(10) + Math.max(bars.bottom, keyboard.bottom));
                return insets;
            });
        }
        setContentView(page);
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController bars = getWindow().getInsetsController();
            if (bars != null) bars.setSystemBarsAppearance(0, WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                    | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);
        }

        // Kopf: Titel, Verbindungsstatus, Verbinden-Knopf
        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        page.addView(header);
        LinearLayout titles = new LinearLayout(this);
        titles.setOrientation(LinearLayout.VERTICAL);
        header.addView(titles, new LinearLayout.LayoutParams(0, -2, 1));
        TextView title = text("Pixel-Konsole", 24, TEXT);
        title.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        titles.addView(title);
        LinearLayout stateRow = new LinearLayout(this);
        stateRow.setGravity(Gravity.CENTER_VERTICAL);
        titles.addView(stateRow);
        stateDot = new View(this);
        stateRow.addView(stateDot, new LinearLayout.LayoutParams(dp(8), dp(8)));
        state = text("Nicht verbunden", 13, MUTED);
        state.setPadding(dp(6), 0, 0, 0);
        state.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        stateRow.addView(state);
        connection = pill("Verbinden", true);
        connection.setOnClickListener(view -> {
            if (ready || connecting) stop("Verbindung getrennt");
            else choosePixel(false);
        });
        connection.setOnLongClickListener(view -> { choosePixel(true); return true; });
        header.addView(connection);

        // Reiter
        LinearLayout tabs = new LinearLayout(this);
        tabs.setBackground(round(SURFACE, 22));
        tabs.setPadding(dp(4), dp(4), dp(4), dp(4));
        LinearLayout.LayoutParams tabsParams = new LinearLayout.LayoutParams(-1, -2);
        tabsParams.topMargin = dp(12);
        page.addView(tabs, tabsParams);
        tabAgent = tab("Agent");
        tabConsole = tab("Konsole");
        tabs.addView(tabAgent, new LinearLayout.LayoutParams(0, dp(38), 1));
        tabs.addView(tabConsole, new LinearLayout.LayoutParams(0, dp(38), 1));
        tabAgent.setOnClickListener(view -> showTab(true));
        tabConsole.setOnClickListener(view -> showTab(false));

        FrameLayout panes = new FrameLayout(this);
        LinearLayout.LayoutParams panesParams = new LinearLayout.LayoutParams(-1, 0, 1);
        panesParams.topMargin = dp(10);
        page.addView(panes, panesParams);
        agentPane = buildAgentPane();
        consolePane = buildConsolePane();
        panes.addView(agentPane, new FrameLayout.LayoutParams(-1, -1));
        panes.addView(consolePane, new FrameLayout.LayoutParams(-1, -1));

        slashScroll = new HorizontalScrollView(this);
        slashScroll.setHorizontalScrollBarEnabled(false);
        slashRow = new LinearLayout(this);
        slashScroll.addView(slashRow);
        slashScroll.setVisibility(View.GONE);
        LinearLayout.LayoutParams slashParams = new LinearLayout.LayoutParams(-1, -2);
        slashParams.topMargin = dp(6);
        page.addView(slashScroll, slashParams);

        // Eingabezeile
        LinearLayout bar = new LinearLayout(this);
        bar.setGravity(Gravity.BOTTOM);
        LinearLayout.LayoutParams barParams = new LinearLayout.LayoutParams(-1, -2);
        barParams.topMargin = dp(10);
        page.addView(bar, barParams);
        input = new EditText(this);
        input.setTextColor(TEXT);
        input.setHintTextColor(MUTED);
        input.setTextSize(15);
        input.setBackground(round(SURFACE, 22));
        input.setPadding(dp(16), dp(11), dp(16), dp(11));
        input.setMaxLines(5);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE
                | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        input.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(4096)});
        input.setImeOptions(EditorInfo.IME_ACTION_SEND);
        bar.addView(input, new LinearLayout.LayoutParams(0, -2, 1));
        input.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence text, int start, int count, int after) { }
            @Override public void onTextChanged(CharSequence text, int start, int before, int count) { }
            @Override public void afterTextChanged(Editable text) { suggest(text.toString()); }
        });
        stopButton = roundButton("■", ERROR);
        stopButton.setContentDescription("Laufenden Auftrag abbrechen");
        stopButton.setOnClickListener(view -> transmit(new byte[]{3}));
        LinearLayout.LayoutParams stopParams = new LinearLayout.LayoutParams(dp(46), dp(46));
        stopParams.leftMargin = dp(8);
        bar.addView(stopButton, stopParams);
        send = roundButton("➤", ACCENT_DARK);
        send.setContentDescription("Senden");
        send.setOnClickListener(view -> submit());
        LinearLayout.LayoutParams sendParams = new LinearLayout.LayoutParams(dp(46), dp(46));
        sendParams.leftMargin = dp(8);
        bar.addView(send, sendParams);
        needsConnection.add(send);

        showTab(true);
        message("Nicht verbunden", MUTED);
        render();
        String saved = prefs.getString("device", null);
        if (saved != null && hasPermission()) main.post(() -> connectSaved(saved));
    }

    // ---------- Aufbau der beiden Ansichten ----------

    private View buildAgentPane() {
        LinearLayout pane = new LinearLayout(this);
        pane.setOrientation(LinearLayout.VERTICAL);

        HorizontalScrollView chipScroll = new HorizontalScrollView(this);
        chipScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout chips = new LinearLayout(this);
        chipScroll.addView(chips);
        pane.addView(chipScroll);
        for (int i = 0; i < PROVIDERS.length; i++) {
            final int index = i;
            TextView chip = chip(PROVIDERS[i]);
            chip.setOnClickListener(view -> {
                provider = index;
                prefs.edit().putInt("provider", index).apply();
                renderProviders();
                toast(PROVIDER_HINTS[index]);
            });
            providerChips.add(chip);
            chips.addView(chip, chipParams());
        }
        renderProviders();
        TextView sessionsChip = chip("Gespräche");
        sessionsChip.setTextColor(TEXT);
        sessionsChip.setBackground(round(SURFACE_HIGH, 18));
        sessionsChip.setOnClickListener(view -> listSessions());
        needsConnection.add(sessionsChip);
        chips.addView(sessionsChip, chipParams());

        chatScroll = new ScrollView(this);
        chatScroll.setFillViewport(true);
        chat = new LinearLayout(this);
        chat.setOrientation(LinearLayout.VERTICAL);
        chat.setPadding(0, dp(6), 0, dp(6));
        chatScroll.addView(chat);
        LinearLayout.LayoutParams chatParams = new LinearLayout.LayoutParams(-1, 0, 1);
        chatParams.topMargin = dp(8);
        pane.addView(chatScroll, chatParams);
        system("Schreib einen Auftrag an Hermes oder tippe / für Befehle. Hermes merkt sich das Gespräch, "
                + "bis du /neu sendest. Lange auf eine Antwort drücken kopiert sie.");

        HorizontalScrollView quickScroll = new HorizontalScrollView(this);
        quickScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout quick = new LinearLayout(this);
        quickScroll.addView(quick);
        pane.addView(quickScroll);
        quickAction(quick, "Status", "Status",
                "echo \"Akku: $(cat /sys/class/power_supply/qcom-battery/capacity)% ($(cat /sys/class/power_supply/qcom-battery/status))\";"
                + " echo \"Energie: $(blueline-powerd status 2>/dev/null | sed -n 's/^modus=//p')\";"
                + " echo \"Netz: $(nmcli -t -f DEVICE,STATE,CONNECTION dev 2>/dev/null | grep -E '^(wlan0|bnep)' | cut -d: -f2- | tr '\\n' ' ')\";"
                + " echo \"Speicher frei: $(df -h / | awk 'NR==2{print $4}')\"; uptime -p");
        quickAction(quick, "Akku", "Akku",
                "b=/sys/class/power_supply/qcom-battery; echo \"$(cat $b/capacity)% · $(cat $b/status)\";"
                + " echo \"Temperatur: $(( $(cat $b/temp) / 10 )) °C\"");
        quickAction(quick, "WLAN", "WLAN",
                "nmcli -t -f ACTIVE,SSID,SIGNAL dev wifi 2>/dev/null | grep '^yes' | cut -d: -f2- | sed 's/:/ · Signal /'"
                + " | grep . || echo 'Kein WLAN'; ip -4 -br addr show wlan0 2>/dev/null | awk '{print \"IP: \"$3}'");
        quickAction(quick, "Taschenlampe", "Taschenlampe",
                "f=/sys/class/leds/white:flash/brightness; if [ \"$(cat $f)\" -gt 0 ]; then echo 0 > $f;"
                + " echo 'Taschenlampe aus'; else echo 64 > $f; echo 'Taschenlampe an'; fi");
        quickAction(quick, "Bildschirm an", "Bildschirm",
                "hyprctl dispatch 'hl.dsp.dpms({ action = \"enable\" })' >/dev/null && echo 'Bildschirm an'");
        quickAction(quick, "Agenten prüfen", "Agenten",
                "curl -s -o /dev/null -w 'Mac-Modell: %{http_code}\\n' --max-time 3 http://127.0.0.1:11234/v1/models"
                + " | sed 's/: 200/: erreichbar/; s/: 000/: nicht erreichbar/';"
                + " curl -s -o /dev/null -w 'Internet: %{http_code}\\n' --max-time 5 https://example.com"
                + " | sed 's/: 200/: ok/; s/: 000/: keine Verbindung/'");
        return pane;
    }

    private View buildConsolePane() {
        LinearLayout pane = new LinearLayout(this);
        pane.setOrientation(LinearLayout.VERTICAL);
        outputScroll = new ScrollView(this);
        outputScroll.setFillViewport(true);
        outputScroll.setBackground(round(0xff0a0d15, 16));
        pane.addView(outputScroll, new LinearLayout.LayoutParams(-1, 0, 1));
        terminal = new TextView(this);
        terminal.setTypeface(Typeface.MONOSPACE);
        terminal.setTextSize(12.5f);
        terminal.setTextColor(0xffcfe0ff);
        terminal.setPadding(dp(12), dp(10), dp(12), dp(10));
        terminal.setTextIsSelectable(true);
        console.append("Befehle laufen als Benutzer omarchy auf dem Pixel.\n");
        terminal.setText(console);
        outputScroll.addView(terminal);
        return pane;
    }

    private void quickAction(LinearLayout row, String label, String title, String command) {
        actions.put(title.toLowerCase(Locale.ROOT), new String[]{title, command});
        TextView chip = chip(label);
        chip.setTextColor(TEXT);
        chip.setBackground(round(SURFACE_HIGH, 18));
        chip.setOnClickListener(view -> {
            if (!ready) { toast("Zuerst das Pixel verbinden"); return; }
            if (running > 0) { toast("Es läuft noch ein Auftrag"); return; }
            runBlock(title, command, false);
        });
        needsConnection.add(chip);
        row.addView(chip, chipParams());
    }

    // ---------- Senden ----------

    private void submit() {
        if (!ready) return;
        String text = input.getText().toString().trim();
        if (text.isEmpty()) return;
        input.setText("");
        String line = text.replace('\r', ' ').replace('\n', ' ');
        if (!agentTab) {
            appendConsole("$ " + line + "\n");
            transmit((line + "\n").getBytes(StandardCharsets.UTF_8));
            return;
        }
        if (text.startsWith("/")) {
            slash(text);
            return;
        }
        bubble(text, true);
        if (running > 0) {
            // Rueckfrage des laufenden Auftrags beantworten
            transmit((line + "\n").getBytes(StandardCharsets.UTF_8));
            return;
        }
        String command = "pixel-agent " + ROUTES[provider] + " " + (sessionId == null ? "-" : sessionId)
                + " " + quote(line);
        runBlock(PROVIDERS[provider] + (sessionId == null ? "" : " · Gespräch"), command, true);
    }

    private static String quote(String text) { return "'" + text.replace("'", "'\\''") + "'"; }

    private void slash(String text) {
        String[] parts = text.trim().split("\\s+", 2);
        String name = parts[0].toLowerCase(Locale.ROOT);
        String arg = parts.length > 1 ? parts[1].trim() : "";
        input.setText("");
        switch (name) {
            case "/hilfe": case "/help": {
                StringBuilder help = new StringBuilder();
                for (String[] entry : SLASH) help.append(entry[0]).append(" – ").append(entry[1]).append('\n');
                help.append("\nAlles ohne / geht als Auftrag an Hermes.");
                note("Befehle", help.toString().trim());
                return;
            }
            case "/neu": case "/new":
                sessionId = null;
                prefs.edit().remove("session").apply();
                note("Neues Gespräch", "Der nächste Auftrag beginnt ohne Vorwissen.");
                return;
            case "/modell": case "/model": {
                int chosen = arg.startsWith("api") || arg.startsWith("anti") ? 1
                        : arg.startsWith("off") ? 2 : arg.startsWith("auto") ? 0 : -1;
                if (chosen < 0) { note("Modell", "Aktuell: " + PROVIDERS[provider] + "\n/modell auto | api | offline"); return; }
                provider = chosen;
                prefs.edit().putInt("provider", chosen).apply();
                renderProviders();
                note("Modell", PROVIDERS[chosen] + " – " + PROVIDER_HINTS[chosen]);
                return;
            }
            case "/gespraeche": case "/gespräche": case "/sessions": case "/verlauf":
                listSessions();
                return;
            case "/stopp": case "/stop":
                transmit(new byte[]{3});
                return;
            default:
        }
        if (!ready) { toast("Zuerst das Pixel verbinden"); return; }
        if (running > 0) { toast("Es läuft noch ein Auftrag – /stopp bricht ab"); return; }
        String key = name.substring(1);
        String[] action = actions.get(key.equals("licht") ? "taschenlampe" : key);
        if (action != null) { runBlock(action[0], action[1], false); return; }
        switch (name) {
            case "/hell": {
                int value = percent(arg);
                if (value < 0) { note("Helligkeit", "/hell 0–100"); return; }
                runBlock("Helligkeit", "brightnessctl --class=backlight --quiet set " + Math.max(1, value)
                        + "% && echo \"Helligkeit " + value + " %\"", false);
                return;
            }
            case "/laut": {
                int value = percent(arg);
                if (value < 0) { note("Lautstärke", "/laut 0–100"); return; }
                runBlock("Lautstärke", "pamixer --set-volume " + value + " && echo \"Lautstärke " + value + " %\"", false);
                return;
            }
            case "/name":
                if (sessionId == null) { note("Gespräch benennen", "Es läuft noch kein Gespräch."); return; }
                if (arg.isEmpty()) { note("Gespräch benennen", "/name TITEL"); return; }
                runBlock("Umbenennen", "pixel-agent rename " + sessionId + " " + quote(arg), false);
                return;
            case "/sperren":
                runBlock("Sperren", "omarchy-system-lock && echo 'Pixel gesperrt'", false);
                return;
            case "/sh":
                if (arg.isEmpty()) { note("Shell", "/sh BEFEHL – zum Beispiel /sh df -h"); return; }
                runBlock("$ " + arg, arg, false);
                return;
            default:
                note("Unbekannter Befehl", name + " gibt es nicht. /hilfe zeigt alle Befehle.");
        }
    }

    private static int percent(String text) {
        try {
            int value = Integer.parseInt(text.replace("%", "").trim());
            return value >= 0 && value <= 100 ? value : -1;
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    private void listSessions() {
        if (!ready) { toast("Zuerst das Pixel verbinden"); return; }
        if (running > 0) { toast("Es läuft noch ein Auftrag"); return; }
        sessions.clear();
        listing = true;
        running++;
        blockText = null;
        transmit("printf '\\036S\\n'; pixel-agent sessions 20; printf '\\036E%d\\n' \"$?\"\n"
                .getBytes(StandardCharsets.UTF_8));
        render();
    }

    private void showSessions() {
        List<String> labels = new ArrayList<>();
        labels.add("＋  Neues Gespräch");
        for (String[] entry : sessions) {
            String mark = entry[0].equals(sessionId) ? "●  " : "";
            labels.add(mark + entry[1] + (entry[2].isEmpty() ? "" : "  ·  " + entry[2]));
        }
        new AlertDialog.Builder(this).setTitle("Gespräche")
                .setItems(labels.toArray(new String[0]), (dialog, which) -> {
                    if (which == 0) {
                        slash("/neu");
                        return;
                    }
                    String[] entry = sessions.get(which - 1);
                    sessionId = entry[0];
                    prefs.edit().putString("session", sessionId).apply();
                    note("Gespräch fortgesetzt", entry[1]);
                })
                .setNegativeButton("Schließen", null).show();
    }

    private void suggest(String text) {
        if (slashRow == null) return;
        slashRow.removeAllViews();
        boolean show = agentTab && text.startsWith("/") && !text.contains(" ");
        if (show) {
            String typed = text.toLowerCase(Locale.ROOT);
            for (String[] entry : SLASH) {
                if (!entry[0].startsWith(typed)) continue;
                TextView chip = chip(entry[0] + "  " + entry[1]);
                chip.setTextColor(TEXT);
                chip.setBackground(round(SURFACE_HIGH, 18));
                chip.setOnClickListener(view -> {
                    boolean takesArg = entry[0].equals("/modell") || entry[0].equals("/hell")
                            || entry[0].equals("/laut") || entry[0].equals("/sh");
                    if (takesArg) {
                        input.setText(entry[0] + " ");
                        input.setSelection(input.getText().length());
                    } else {
                        slash(entry[0]);
                    }
                });
                slashRow.addView(chip, chipParams());
            }
            show = slashRow.getChildCount() > 0;
        }
        slashScroll.setVisibility(show ? View.VISIBLE : View.GONE);
    }

    private void note(String title, String body) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackground(outline());
        card.setPadding(dp(14), dp(10), dp(14), dp(12));
        card.addView(text(title, 12, ACCENT));
        TextView content = text(body, 14, TEXT);
        content.setPadding(0, dp(4), 0, 0);
        content.setLineSpacing(0, 1.15f);
        card.addView(content);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.topMargin = dp(8);
        chat.addView(card, params);
        showTab(true);
        scrollChat();
    }

    private void runBlock(String title, String command, boolean agent) {
        running++;
        openBlock(title, agent);
        String wrapped = "printf '\\036S\\n'; " + command + "; printf '\\036E%d\\n' \"$?\"\n";
        transmit(wrapped.getBytes(StandardCharsets.UTF_8));
        render();
    }

    // ---------- Bluetooth ----------

    private boolean hasPermission() {
        return Build.VERSION.SDK_INT < 31 || checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)
                == PackageManager.PERMISSION_GRANTED;
    }

    private BluetoothAdapter adapter() {
        BluetoothManager manager = getSystemService(BluetoothManager.class);
        return manager == null ? null : manager.getAdapter();
    }

    private void connectSaved(String address) {
        BluetoothAdapter adapter = adapter();
        if (adapter == null || !adapter.isEnabled()) return;
        try {
            for (BluetoothDevice device : adapter.getBondedDevices()) {
                if (device.getAddress().equals(address)) { connect(device); return; }
            }
        } catch (SecurityException ignored) {
            // Ohne Berechtigung verbindet der Knopf.
        }
    }

    private void choosePixel(boolean forceList) {
        if (!hasPermission()) {
            requestPermissions(new String[]{Manifest.permission.BLUETOOTH_CONNECT}, PERMISSION);
            return;
        }
        BluetoothAdapter adapter = adapter();
        if (adapter == null) { message("Bluetooth ist nicht verfügbar", ERROR); return; }
        if (!adapter.isEnabled()) { message("Schalte Bluetooth ein", WARN); openSettings(); return; }
        String saved = prefs.getString("device", null);
        List<BluetoothDevice> devices = new ArrayList<>(adapter.getBondedDevices());
        if (!forceList && saved != null) {
            for (BluetoothDevice device : devices) {
                if (device.getAddress().equals(saved)) { connect(device); return; }
            }
        }
        if (devices.isEmpty()) { message("Kopple zuerst das Pixel", WARN); openSettings(); return; }
        String[] names = devices.stream().map(this::deviceName).toArray(String[]::new);
        new AlertDialog.Builder(this).setTitle("Pixel auswählen")
                .setItems(names, (dialog, which) -> connect(devices.get(which)))
                .setNeutralButton("Bluetooth-Einstellungen", (dialog, button) -> openSettings())
                .setNegativeButton("Abbrechen", null).show();
    }

    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(request, permissions, results);
        if (request != PERMISSION) return;
        if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) choosePixel(false);
        else message("Erlaube den Zugriff auf Geräte in der Nähe", WARN);
    }

    private String deviceName(BluetoothDevice device) {
        String name;
        try {
            name = device.getName();
        } catch (SecurityException e) {
            name = null;
        }
        return name == null || name.trim().isEmpty() ? device.getAddress() : name;
    }

    private void connect(BluetoothDevice device) { connect(device, true); }

    private void connect(BluetoothDevice device, boolean retry) {
        String name = deviceName(device);
        int current = ++generation;
        connecting = true;
        synchronized (pending) {
            pending.setLength(0);
            pendingGeneration = current;
        }
        resetParser();
        message("Verbinde mit " + name + " …", WARN);
        render();
        Runnable expiry = () -> {
            if (generation == current && connecting) stop("Das Pixel hat nicht geantwortet");
        };
        main.postDelayed(expiry, 20_000);
        reader.execute(() -> openSession(device, name, current, expiry, retry));
    }

    private synchronized boolean register(BluetoothSocket candidate, int current) {
        if (generation != current) return false;
        socket = candidate;
        return true;
    }

    private void openSession(BluetoothDevice device, String name, int current, Runnable expiry, boolean retry) {
        boolean opened = false;
        try (BluetoothSocket candidate = device.createRfcommSocketToServiceRecord(SERVICE)) {
            if (!register(candidate, current)) return;
            candidate.connect();
            candidate.getOutputStream().write("{\"action\":\"terminal\"}\n".getBytes(StandardCharsets.UTF_8));
            candidate.getOutputStream().flush();
            InputStream stream = candidate.getInputStream();
            JSONObject reply = new JSONObject(readReply(stream));
            if (!reply.optBoolean("ok")) throw new IOException("Terminal unavailable");
            // Ohne Zeileneditor und Echo kommt nur die Ausgabe zurueck.
            candidate.getOutputStream().write(("set +o emacs +o vi; stty -echo; PS1=; PS2=; "
                    + "export NO_COLOR=1 TERM=dumb; printf '\\036R\\n'\n").getBytes(StandardCharsets.UTF_8));
            candidate.getOutputStream().flush();
            opened = true;
            main.post(() -> {
                if (generation != current) return;
                main.removeCallbacks(expiry);
                connecting = false;
                ready = true;
                prefs.edit().putString("device", device.getAddress()).apply();
                message("Verbunden mit " + name, OK);
                render();
            });
            InputStreamReader text = new InputStreamReader(stream, StandardCharsets.UTF_8);
            char[] buffer = new char[4096];
            int length;
            while ((length = text.read(buffer)) != -1 && generation == current) {
                queueOutput(buffer, length, current);
            }
        } catch (IOException | JSONException | SecurityException failure) {
            // Verweigerte Freigabe oder getrennte Verbindung beenden die Sitzung.
        } finally {
            String note = opened ? "Verbindung beendet" : "Verbindung fehlgeschlagen – Freigabe am Pixel prüfen";
            boolean again = !opened && retry;
            main.post(() -> {
                main.removeCallbacks(expiry);
                if (generation != current) return;
                if (again) {
                    // Das Pixel haelt eine eben getrennte Sitzung noch kurz offen.
                    message("Neuer Versuch …", WARN);
                    main.postDelayed(() -> { if (generation == current) connect(device, false); }, 3000);
                } else {
                    stop(note);
                }
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

    private void transmit(byte[] message) {
        BluetoothSocket current = socket;
        if (!ready || current == null) return;
        writer.execute(() -> {
            try {
                current.getOutputStream().write(message);
                current.getOutputStream().flush();
            } catch (IOException failure) {
                main.post(() -> {
                    if (socket == current) stop("Bluetooth-Verbindung getrennt");
                });
            }
        });
    }

    // ---------- Ausgabe verarbeiten ----------

    private void queueOutput(char[] chars, int length, int current) {
        synchronized (pending) {
            if (generation != current) return;
            pendingGeneration = current;
            pending.append(chars, 0, length);
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
            if (owner == generation) consume(text);
        });
    }

    private void resetParser() {
        escapeState = 0;
        markState = 0;
        markLine.setLength(0);
        inBlock = false;
        running = 0;
    }

    private void consume(String text) {
        StringBuilder plain = new StringBuilder();
        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            if (markState == 1) {
                markKind = ch;
                markState = 2;
                markLine.setLength(0);
                continue;
            }
            if (markState == 2) {
                if (ch == '\n') {
                    flushPlain(plain);
                    handleMark(markKind, markLine.toString());
                    markState = 0;
                } else if (ch != '\r') {
                    markLine.append(ch);
                }
                continue;
            }
            if (ch == MARK) {
                markState = 1;
                continue;
            }
            switch (escapeState) {
                case 1: escapeState = ch == '[' ? 2 : ch == ']' ? 3 : 0; break;
                case 2: if (ch >= '@' && ch <= '~') escapeState = 0; break;
                case 3: if (ch == '\u0007') escapeState = 0; else if (ch == '\u001b') escapeState = 4; break;
                case 4: escapeState = ch == '\\' ? 0 : 3; break;
                default:
                    if (ch == '\u001b') escapeState = 1;
                    else if (ch == '\n' || ch == '\t' || !Character.isISOControl(ch)) plain.append(ch);
            }
        }
        flushPlain(plain);
    }

    private void flushPlain(StringBuilder plain) {
        if (plain.length() == 0) return;
        String chunk = plain.toString();
        plain.setLength(0);
        if (inBlock && blockText != null) {
            blockText.append(chunk);
            String shown = blockText.toString().replaceAll("(?m)^session_id: .*$", "").trim();
            blockView.setText(shown.isEmpty() ? "…" : shown);
            scrollChat();
        } else {
            appendConsole(chunk);
        }
    }

    private void handleMark(char kind, String rest) {
        if (kind == 'L') {
            String[] parts = rest.split("\t", 3);
            if (listing && parts.length == 3 && parts[0].matches("[A-Za-z0-9._:-]+")) {
                sessions.add(new String[]{parts[0], parts[1].isEmpty() ? "(ohne Titel)" : parts[1], parts[2]});
            }
        } else if (kind == 'I') {
            String id = rest.trim();
            if (id.matches("[A-Za-z0-9._:-]+")) {
                sessionId = id;
                prefs.edit().putString("session", id).apply();
            }
        } else if (kind == 'R') {
            // Shell eingerichtet: das Echo der Einrichtungszeile verwerfen.
            console.setLength(0);
            console.append("Befehle laufen als Benutzer omarchy auf dem Pixel.\n");
            terminal.setText(console);
        } else if (kind == 'S') {
            inBlock = true;
        } else if (kind == 'E') {
            inBlock = false;
            if (running > 0) running--;
            if (listing) {
                listing = false;
                render();
                showSessions();
                return;
            }
            String code = rest.trim();
            boolean ok = code.equals("0");
            boolean cancelled = code.equals("130");
            if (blockMeta != null) {
                blockMeta.setText(blockMeta.getText().toString().replace(" · läuft …", "")
                        + (ok ? " · fertig" : cancelled ? " · abgebrochen" : " · Fehler " + code));
                blockMeta.setTextColor(ok ? OK : cancelled ? WARN : ERROR);
            }
            if (blockText != null && blockText.toString().trim().isEmpty() && blockView != null) {
                blockView.setText(ok ? "Erledigt." : "Keine Ausgabe.");
            }
            blockText = null;
            render();
        }
    }

    private void appendConsole(String chunk) {
        console.append(chunk);
        if (console.length() > HISTORY_LIMIT) console.delete(0, console.length() - HISTORY_LIMIT);
        terminal.setText(console);
        outputScroll.post(() -> outputScroll.scrollTo(0, terminal.getHeight()));
    }

    // ---------- Chat-Elemente ----------

    private void openBlock(String title, boolean agent) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackground(round(SURFACE, 18));
        card.setPadding(dp(14), dp(10), dp(14), dp(12));
        blockMeta = text((agent ? "Hermes · " : "") + title + " · läuft …", 12, ACCENT);
        card.addView(blockMeta);
        blockView = text("…", 15, TEXT);
        blockView.setLineSpacing(0, 1.15f);
        blockView.setPadding(0, dp(4), 0, 0);
        TextView target = blockView;
        card.setOnLongClickListener(view -> {
            copy(target.getText().toString());
            return true;
        });
        card.addView(blockView);
        blockText = new StringBuilder();
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2);
        params.topMargin = dp(8);
        params.rightMargin = dp(36);
        chat.addView(card, params);
        scrollChat();
    }

    private void bubble(String text, boolean mine) {
        TextView view = text(text, 15, mine ? 0xffffffff : TEXT);
        view.setBackground(round(mine ? ACCENT_DARK : SURFACE, 18));
        view.setPadding(dp(14), dp(10), dp(14), dp(10));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-2, -2);
        params.topMargin = dp(8);
        params.gravity = mine ? Gravity.END : Gravity.START;
        if (mine) params.leftMargin = dp(48);
        chat.addView(view, params);
        scrollChat();
    }

    private void system(String text) {
        TextView view = text(text, 13, MUTED);
        view.setGravity(Gravity.CENTER);
        view.setPadding(dp(12), dp(8), dp(12), dp(8));
        chat.addView(view, new LinearLayout.LayoutParams(-1, -2));
    }

    private void scrollChat() { chatScroll.post(() -> chatScroll.fullScroll(View.FOCUS_DOWN)); }

    private void copy(String text) {
        ClipboardManager clipboard = getSystemService(ClipboardManager.class);
        if (clipboard == null) return;
        clipboard.setPrimaryClip(ClipData.newPlainText("Antwort", text));
        toast("Kopiert");
    }

    // ---------- Zustand ----------

    private synchronized void stop(String note) {
        generation++;
        BluetoothSocket previous = socket;
        socket = null;
        if (previous != null) {
            try {
                previous.close();
            } catch (IOException ignored) {
                // Bereits getrennt.
            }
        }
        connecting = false;
        ready = false;
        listing = false;
        if (inBlock || running > 0) handleMark('E', "1");
        resetParser();
        message(note, MUTED);
        render();
    }

    private void showTab(boolean agent) {
        agentTab = agent;
        agentPane.setVisibility(agent ? View.VISIBLE : View.GONE);
        consolePane.setVisibility(agent ? View.GONE : View.VISIBLE);
        styleTab(tabAgent, agent);
        styleTab(tabConsole, !agent);
        input.setHint(agent ? "Auftrag an Hermes oder / …" : "Befehl für das Pixel …");
        if (input != null) suggest(input.getText().toString());
        if (stopButton != null) render();
    }

    private void render() {
        connection.setText(connecting ? "Abbrechen" : ready ? "Trennen" : "Verbinden");
        for (View view : needsConnection) {
            view.setEnabled(ready);
            view.setAlpha(ready ? 1f : 0.45f);
        }
        input.setEnabled(ready);
        stopButton.setVisibility(ready && (running > 0 || !agentTab) ? View.VISIBLE : View.GONE);
    }

    private void renderProviders() {
        for (int i = 0; i < providerChips.size(); i++) {
            TextView chip = providerChips.get(i);
            boolean selected = i == provider;
            chip.setBackground(selected ? round(ACCENT, 18) : outline());
            chip.setTextColor(selected ? 0xff0b1020 : MUTED);
        }
    }

    private void message(String text, int color) {
        state.setText(text);
        state.setTextColor(color == OK ? TEXT : color);
        GradientDrawable dot = new GradientDrawable();
        dot.setShape(GradientDrawable.OVAL);
        dot.setColor(color);
        stateDot.setBackground(dot);
    }

    // ---------- Bausteine ----------

    private TextView text(String value, float size, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        return view;
    }

    private TextView tab(String label) {
        TextView view = text(label, 14, MUTED);
        view.setGravity(Gravity.CENTER);
        view.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        return view;
    }

    private void styleTab(TextView view, boolean selected) {
        view.setBackground(selected ? round(SURFACE_HIGH, 18) : null);
        view.setTextColor(selected ? TEXT : MUTED);
    }

    private TextView chip(String label) {
        TextView view = text(label, 13, MUTED);
        view.setPadding(dp(14), 0, dp(14), 0);
        view.setGravity(Gravity.CENTER);
        return view;
    }

    private LinearLayout.LayoutParams chipParams() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-2, dp(34));
        params.rightMargin = dp(8);
        params.topMargin = dp(4);
        return params;
    }

    private Button pill(String label, boolean primary) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setTextColor(primary ? 0xffffffff : TEXT);
        button.setBackground(round(primary ? ACCENT_DARK : SURFACE_HIGH, 20));
        button.setPadding(dp(18), 0, dp(18), 0);
        button.setMinHeight(dp(40));
        button.setMinimumHeight(dp(40));
        button.setStateListAnimator(null);
        return button;
    }

    private Button roundButton(String label, int color) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(16);
        button.setTextColor(0xffffffff);
        GradientDrawable shape = new GradientDrawable();
        shape.setShape(GradientDrawable.OVAL);
        shape.setColor(color);
        button.setBackground(shape);
        button.setPadding(0, 0, 0, 0);
        button.setStateListAnimator(null);
        return button;
    }

    private GradientDrawable round(int color, int radius) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radius));
        return shape;
    }

    private GradientDrawable outline() {
        GradientDrawable shape = round(0x00000000, 18);
        shape.setStroke(dp(1), 0xff33405c);
        return shape;
    }

    private void toast(String text) { Toast.makeText(this, text, Toast.LENGTH_SHORT).show(); }
    private void openSettings() { startActivity(new Intent(Settings.ACTION_BLUETOOTH_SETTINGS)); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override protected void onDestroy() {
        stop("Verbindung getrennt");
        reader.shutdownNow();
        writer.shutdownNow();
        main.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}
