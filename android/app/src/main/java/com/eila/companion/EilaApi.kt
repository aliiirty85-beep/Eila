package com.eila.companion

import android.content.Context
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class EilaApi(context:Context){
    private val prefs=AppPrefs(context)
    private val client=OkHttpClient.Builder().connectTimeout(4,TimeUnit.SECONDS).readTimeout(8,TimeUnit.SECONDS).build()
    private val json="application/json; charset=utf-8".toMediaType()
    private fun req(path:String,method:String="GET",body:JSONObject?=null):Request{
        val b=Request.Builder().url(prefs.serverUrl+path).header("X-Eila-Token",prefs.pairingToken)
        if(method=="POST")b.post((body?:JSONObject()).toString().toRequestBody(json))
        return b.build()
    }
    fun post(path:String,body:JSONObject):JSONObject?=try{client.newCall(req(path,"POST",body)).execute().use{r->if(!r.isSuccessful)return null;JSONObject(r.body?.string()?:"{}")}}catch(_:Exception){null}
    fun get(path:String):JSONObject?=try{client.newCall(req(path)).execute().use{r->if(!r.isSuccessful)return null;JSONObject(r.body?.string()?:"{}")}}catch(_:Exception){null}
    fun heartbeat(state:JSONObject=JSONObject()):Boolean{val o=JSONObject().put("device_id",prefs.deviceId).put("kind","android").put("name",prefs.deviceName).put("capabilities",JSONObject().put("camera",true).put("tts",true).put("vibrate",true).put("local_return",true)).put("state",state);return post("/api/device/heartbeat",o)!=null}
    fun sendGaze(o:JSONObject):Boolean{o.put("device_id",prefs.deviceId);return post("/api/gaze",o)!=null}
    fun commands():JSONArray=get("/api/device/${prefs.deviceId}/commands")?.optJSONArray("commands")?:JSONArray()
    fun ack(id:Long){post("/api/device/${prefs.deviceId}/commands/$id/ack",JSONObject())}
}
