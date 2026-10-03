package com.example.utilitaria

import android.content.ComponentName
import android.content.Intent
import android.service.notification.NotificationListenerService
import android.provider.Settings
import androidx.core.app.NotificationManagerCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "utilitaria/settings")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "openNotificationAccess" -> {
                        startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                        result.success(true)
                    }
                    "isNotificationAccessGranted" -> result.success(
                        NotificationManagerCompat.getEnabledListenerPackages(this)
                            .contains(packageName)
                    )
                    "rescanNotifications" -> {
                        val listener = UtilitariaNotificationListener.connectedInstance
                        if (listener != null) {
                            listener.rescanActiveNotifications()
                        } else {
                            NotificationListenerService.requestRebind(
                                ComponentName(this, UtilitariaNotificationListener::class.java)
                            )
                        }
                        result.success(true)
                    }
                    else -> result.notImplemented()
                }
            }
    }
}
