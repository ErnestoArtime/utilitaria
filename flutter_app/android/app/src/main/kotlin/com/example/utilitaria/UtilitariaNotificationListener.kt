package com.example.utilitaria

import android.os.Handler
import android.os.Looper
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.Executors

class UtilitariaNotificationListener : NotificationListenerService() {
    companion object {
        @Volatile
        var connectedInstance: UtilitariaNotificationListener? = null
            private set
    }

    private val executor = Executors.newSingleThreadExecutor()
    private val handler = Handler(Looper.getMainLooper())
    private val queueLock = Any()
    private val retryTask = object : Runnable {
        override fun run() {
            flushPending()
            handler.postDelayed(this, 30_000)
        }
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val extras = sbn.notification.extras
        val title = extras.getString("android.title") ?: ""
        val body = extras.getCharSequence("android.text")?.toString() ?: return
        if (title.isBlank() || body.isBlank() || !isIngBankOperation(sbn.packageName, title, body)) return

        val externalId = stableExternalId(sbn, title, body)
        val captured = getSharedPreferences("captured_notifications", MODE_PRIVATE)
        if (captured.contains(externalId) || queueContains(externalId)) return

        enqueue(
            JSONObject()
                .put("external_id", externalId)
                .put("package_name", sbn.packageName)
                .put("title", title)
                .put("body", body)
                .put("received_at", isoDate(sbn.postTime))
                .put("category", "other")
                .put("is_business", false)
                .put("shared_with_family", false)
                .put("attempts", 0)
                .put("next_attempt_at", 0L)
        )
        flushPending()
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        connectedInstance = this
        rescanActiveNotifications()
        handler.removeCallbacks(retryTask)
        handler.post(retryTask)
    }

    fun rescanActiveNotifications() {
        activeNotifications?.forEach(::onNotificationPosted)
        flushPending()
    }

    override fun onListenerDisconnected() {
        connectedInstance = null
        super.onListenerDisconnected()
    }

    private fun enqueue(item: JSONObject) = synchronized(queueLock) {
        val queue = readQueue()
        while (queue.length() >= 500) queue.remove(0)
        queue.put(item)
        saveQueue(queue)
    }

    private fun queueContains(externalId: String): Boolean = synchronized(queueLock) {
        val queue = readQueue()
        (0 until queue.length()).any {
            queue.optJSONObject(it)?.optString("external_id") == externalId
        }
    }

    private fun flushPending() {
        executor.execute {
            synchronized(queueLock) {
                val queue = readQueue()
                val remaining = JSONArray()
                val now = System.currentTimeMillis()
                for (index in 0 until queue.length()) {
                    val item = queue.optJSONObject(index) ?: continue
                    if (item.optLong("next_attempt_at", 0L) > now) {
                        remaining.put(item)
                        continue
                    }
                    if (sendNotification(item)) {
                        getSharedPreferences("captured_notifications", MODE_PRIVATE)
                            .edit()
                            .putLong(item.getString("external_id"), now)
                            .apply()
                    } else {
                        val attempts = item.optInt("attempts", 0) + 1
                        val delay = minOf(3_600_000L, 15_000L * (1L shl minOf(attempts - 1, 8)))
                        item.put("attempts", attempts)
                        item.put("next_attempt_at", now + delay)
                        remaining.put(item)
                    }
                }
                saveQueue(remaining)
            }
        }
    }

    private fun readQueue(): JSONArray {
        val raw = getSharedPreferences("notification_outbox", MODE_PRIVATE)
            .getString("pending", "[]") ?: "[]"
        return try {
            JSONArray(raw)
        } catch (_: Exception) {
            JSONArray()
        }
    }

    private fun saveQueue(queue: JSONArray) {
        getSharedPreferences("notification_outbox", MODE_PRIVATE)
            .edit()
            .putString("pending", queue.toString())
            .apply()
    }

    private fun accessToken(): String? =
        getSharedPreferences("FlutterSharedPreferences", MODE_PRIVATE)
            .getString("flutter.auth_token", null)
            ?.takeIf { it.isNotBlank() }

    private fun sendNotification(item: JSONObject): Boolean {
        val token = accessToken() ?: return false
        return try {
            val connection = URL("${BuildConfig.UTILITARIA_API_URL}/api/notifications")
                .openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.connectTimeout = 15_000
            connection.readTimeout = 15_000
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Authorization", "Bearer $token")
            val payload = JSONObject(item.toString())
            payload.remove("attempts")
            payload.remove("next_attempt_at")
            connection.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
            val successful = connection.responseCode in 200..299
            if (!successful) Log.w("Utilitaria", "API ${connection.responseCode}")
            connection.disconnect()
            successful
        } catch (error: Exception) {
            Log.e("Utilitaria", "La notificación queda pendiente para reintento", error)
            false
        }
    }

    private fun stableExternalId(sbn: StatusBarNotification, title: String, body: String): String {
        val raw = "${sbn.packageName}|${sbn.postTime}|$title|$body"
        val digest = MessageDigest.getInstance("SHA-256").digest(raw.toByteArray())
        return digest.joinToString("") { "%02x".format(it) }
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

    private fun isoDate(timestamp: Long): String =
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }.format(Date(timestamp))

    override fun onDestroy() {
        connectedInstance = null
        handler.removeCallbacks(retryTask)
        executor.shutdown()
        super.onDestroy()
    }
}
