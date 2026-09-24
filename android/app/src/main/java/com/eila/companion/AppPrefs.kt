package com.eila.companion

import android.content.Context
import java.util.UUID

class AppPrefs(context: Context) {
    private val p=context.getSharedPreferences("eila_prefs",Context.MODE_PRIVATE)
    var serverUrl:String
        get()=p.getString("server_url","http://192.168.1.2:8765")!!.trimEnd('/')
        set(v){p.edit().putString("server_url",v.trim().trimEnd('/')).apply()}
    var pairingToken:String
        get()=p.getString("pairing_token","")?:""
        set(v){p.edit().putString("pairing_token",v.trim()).apply()}
    val deviceId:String
        get(){
            var id=p.getString("device_id",null)
            if(id==null){id="android-"+UUID.randomUUID().toString();p.edit().putString("device_id",id).apply()}
            return id
        }
    var deviceName:String
        get()=p.getString("device_name",android.os.Build.MODEL)?:android.os.Build.MODEL
        set(v){p.edit().putString("device_name",v).apply()}
}
