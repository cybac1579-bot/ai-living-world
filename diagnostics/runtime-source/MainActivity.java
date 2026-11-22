package com.ailivingworld.mobile;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.graphics.Color;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Native Android shell for a PRIVATE Python engine; no WebView OAuth or API tokens. */
public final class MainActivity extends Activity {
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private WebView webView;
    private TextView status;
    private String localOrigin = "";

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        final LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.BLACK);
        final LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        Button offline = new Button(this); offline.setText("화면 시험");
        Button login = new Button(this); login.setText("로그인");
        Button online = new Button(this); online.setText("GPT 플레이");
        bar.addView(offline,new LinearLayout.LayoutParams(0, 56, 1f));
        bar.addView(login,new LinearLayout.LayoutParams(0, 56, 1f));
        bar.addView(online,new LinearLayout.LayoutParams(0, 56, 1f));
        status = new TextView(this);
        status.setText("모의 화면 준비 중 · 공식 게임 저장과 분리돼");
        status.setTextColor(Color.WHITE);
        status.setGravity(Gravity.CENTER_VERTICAL);
        status.setPadding(12, 0, 12, 0);
        root.addView(bar);
        root.addView(status,new LinearLayout.LayoutParams(-1,48));
        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        webView.setWebViewClient(new WebViewClient() {
            private boolean trusted(Uri u) {
                return "http".equals(u.getScheme()) && "127.0.0.1".equals(u.getHost())
                    && u.getPort() > 0 && localOrigin.equals("http://127.0.0.1:" + u.getPort());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, android.webkit.WebResourceRequest request) {
                return !trusted(request.getUrl());
            }
            @Override public void onPageFinished(WebView view, String url) {
                status.setText("비공식 DEMO · 실제 저장 여부는 게임의 rev로 확인해");
            }
        });
        root.addView(webView,new LinearLayout.LayoutParams(-1,0,1f));
        setContentView(root);
        offline.setOnClickListener(v -> startEngine(true));
        login.setOnClickListener(v -> doLogin());
        online.setOnClickListener(v -> startEngine(false));
        startEngine(true);
    }

    private void uiError(String message) {
        runOnUiThread(() -> status.setText(message));
    }
    private void unpackAsset(String asset, File out) throws IOException {
        File parent = out.getParentFile();
        if (parent == null || (!parent.exists() && !parent.mkdirs())) throw new IOException("resource directory");
        File pending = new File(parent, out.getName() + ".pending");
        try (InputStream in = getAssets().open(asset); FileOutputStream fos = new FileOutputStream(pending)) {
            byte[] buffer = new byte[8192]; int n;
            while ((n = in.read(buffer)) != -1) fos.write(buffer,0,n);
            fos.getFD().sync();
        }
        try {
            Files.move(pending.toPath(), out.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (java.nio.file.AtomicMoveNotSupportedException ex) {
            Files.move(pending.toPath(), out.toPath(), StandardCopyOption.REPLACE_EXISTING);
        }
    }
    private File prepareResources() throws IOException {
        File files = new File(getFilesDir(),"resources-v12");
        String[] names={"web/index.html","web/app.js","web/style.css","web/assets/forest.jpg",
                "examples/live_demo_world.json"};
        for(String name:names) {
            File dest = new File(files,name);
            // Resources can be overwritten on upgrade, but not user event journals.
            unpackAsset(name,dest);
        }
        return files;
    }
    private void startEngine(boolean offline) {
        uiError(offline ? "오프라인 화면 실행 중…" : "ChatGPT 연결 중…");
        worker.execute(() -> {
            try {
                File assetsDir = prepareResources();
                PyObject module = Python.getInstance().getModule("mobile_embedded");
                PyObject url = module.callAttr("start_engine",getFilesDir().getCanonicalPath(),
                        assetsDir.getCanonicalPath(),offline);
                String result = url.toString();
                Uri u = Uri.parse(result);
                if (!"127.0.0.1".equals(u.getHost()) || !"http".equals(u.getScheme()))
                    throw new IllegalStateException("unexpected local server address");
                runOnUiThread(() -> {
                    localOrigin = "http://127.0.0.1:" + u.getPort();
                    webView.loadUrl(result);
                });
            } catch (Exception ex) {
                uiError("실행 실패: Android 런타임/인증/리소스를 확인해야 해. (" + ex.getClass().getSimpleName() + ")");
            }
        });
    }
    /** This is called from Python on a worker thread. Never load an auth URL in WebView. */
    public boolean openSystemBrowser(String url) {
        Uri uri = Uri.parse(url);
        if (!"https".equals(uri.getScheme()) || !"auth.openai.com".equals(uri.getHost()) ||
                !"/api/accounts/authorize".equals(uri.getPath())) return false;
        final CountDownLatch opened = new CountDownLatch(1);
        final AtomicBoolean didOpen = new AtomicBoolean(false);
        runOnUiThread(() -> {
            try { startActivity(new Intent(Intent.ACTION_VIEW,uri)); didOpen.set(true); }
            catch (Exception ex) { status.setText("시스템 브라우저를 열지 못했어."); }
            finally { opened.countDown(); }
        });
        try { return opened.await(8, TimeUnit.SECONDS) && didOpen.get(); }
        catch (InterruptedException ex) { Thread.currentThread().interrupt(); return false; }
    }
    private void doLogin() {
        uiError("시스템 브라우저에서 로그인·권한 승인을 진행해줘.");
        worker.execute(() -> {
            try {
                PyObject module = Python.getInstance().getModule("mobile_embedded");
                module.callAttr("login",getFilesDir().getCanonicalPath(),this);
                uiError("인증 확인 완료. GPT 플레이를 눌러줘.");
            } catch (Exception ex) {
                uiError("로그인 미완료. 별도 유료 API로 전환하지 않아. ("+ex.getClass().getSimpleName()+")");
            }
        });
    }
    @Override protected void onDestroy() {
        if(webView!=null) {webView.destroy();webView=null;}
        worker.shutdown();
        super.onDestroy();
        // Python loopback engine lives until process termination; journal is saved per turn.
    }
}
