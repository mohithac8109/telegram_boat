package com.telegrammediamanager

import android.annotation.SuppressLint
import android.content.Context
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private lateinit var urlInput: EditText
    private lateinit var loadButton: Button
    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        urlInput = findViewById(R.id.urlInput)
        loadButton = findViewById(R.id.loadButton)
        webView = findViewById(R.id.webView)

        val prefs = getSharedPreferences("app_config", Context.MODE_PRIVATE)
        val savedUrl = prefs.getString("server_url", "http://<server-ip>:8000") ?: "http://<server-ip>:8000"
        urlInput.setText(savedUrl)

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()

        loadButton.setOnClickListener {
            val url = urlInput.text.toString().trim()
            if (url.isNotEmpty()) {
                prefs.edit().putString("server_url", url).apply()
                webView.loadUrl(url)
            }
        }

        if (savedUrl.isNotBlank() && savedUrl != "http://<server-ip>:8000") {
            webView.loadUrl(savedUrl)
        }
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
