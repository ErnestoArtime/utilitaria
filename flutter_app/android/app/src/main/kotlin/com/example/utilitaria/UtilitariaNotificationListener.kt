package com.example.utilitaria

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.Executors

class UtilitariaNotificationListener : NotificationListenerService() {
    private val executor = Executors.newSingleThreadExecutor()

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        processNotification(sbn)
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        activeNotifications?.forEach(::processNotification)
    }

    private fun processNotification(sbn: StatusBarNotification) {
        val extras = sbn.notification.extras
        val title = extras.getString("android.title") ?: ""
        val body = extras.getCharSequence("android.text")?.toString() ?: return
        if (title.isBlank() || body.isBlank() || !isIngBankOperation(sbn.packageName, title, body)) return

        val preferences = getSharedPreferences("captured_notifications", MODE_PRIVATE)
        if (preferences.contains(sbn.key)) return

        executor.execute {
            if (sendNotification(sbn.key, sbn.packageName, title, body, sbn.postTime)) {
                preferences.edit().putLong(sbn.key, System.currentTimeMillis()).apply()
            }
        }
    }

    private fun isIngBankOperation(packageName: String, title: String, body: String): Boolean {
        val normalizedPackage = packageName.lowercase()
        val isIng = normalizedPackage == "www.ingdirect.nativeframe" ||
            normalizedPackage == "com.ing.mobile" ||
            title.trim().equals("ING", ignoreCase = true)
        if (!isIng) return false

        val text = "$title $body".lowercase()
        return listOf(
            "transferencia", "bizum", "has recibido", "ha recibido",
            "ingreso", "abono", "pago", "pagado", "compra", "cargo", "recibo"
        ).any(text::contains)
    }

    private fun sendNotification(
        externalId: String,
        packageName: String,
        title: String,
        body: String,
        postTime: Long
    ): Boolean {
        return try {
            val connection = URL("${BuildConfig.UTILITARIA_API_URL}/api/notifications")
                .openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.connectTimeout = 15_000
            connection.readTimeout = 15_000
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("X-API-Key", BuildConfig.UTILITARIA_API_KEY)
            val payload = JSONObject()
                .put("external_id", externalId)
                .put("package_name", packageName)
                .put("title", title)
                .put("body", body)
                .put("received_at", isoDate(postTime))
                .put("category", "income")
                .put("is_business", false)
                .put("shared_with_family", false)
                .toString()
            connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val successful = connection.responseCode in 200..299
            if (!successful) android.util.Log.w("Utilitaria", "API ${connection.responseCode}")
            connection.disconnect()
            successful
        } catch (error: Exception) {
            android.util.Log.e("Utilitaria", "No se pudo sincronizar la notificación", error)
            false
        }
    }

    private fun isoDate(timestamp: Long): String =
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }.format(Date(timestamp))

    override fun onDestroy() {
        executor.shutdown()
        super.onDestroy()
    }
}
