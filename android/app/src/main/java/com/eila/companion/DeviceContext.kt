package com.eila.companion

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.PowerManager
import org.json.JSONObject

object DeviceContext{
    fun snapshot(context:Context,faceSeenSecondsAgo:Long):JSONObject{
        val pm=context.getSystemService(PowerManager::class.java)
        val battery=context.registerReceiver(null,IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val status=battery?.getIntExtra(BatteryManager.EXTRA_STATUS,-1)?:-1
        val charging=status==BatteryManager.BATTERY_STATUS_CHARGING||status==BatteryManager.BATTERY_STATUS_FULL
        val level=battery?.getIntExtra(BatteryManager.EXTRA_LEVEL,-1)?:-1
        val scale=battery?.getIntExtra(BatteryManager.EXTRA_SCALE,100)?:100
        val pct=if(level>=0&&scale>0)level*100.0/scale else -1.0
        return JSONObject()
            .put("screen_interactive",pm.isInteractive)
            .put("charging",charging)
            .put("battery_pct",pct)
            .put("face_seen_seconds_ago",faceSeenSecondsAgo)
    }
}
