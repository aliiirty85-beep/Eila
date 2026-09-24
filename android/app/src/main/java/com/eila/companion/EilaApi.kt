package com.eila.companion

import android.content.Context
import android.os.Build
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class EilaApi(private val context:Context){
    private val prefs=AppPrefs(context)
    private val client=OkHttpClient.Builder().connectTimeout(4,TimeUnit.SECONDS).readTimeout(8,TimeUnit.SECONDS).build()
    private val json="application/json; charset=utf-8".toMediaType()

    private fun req(path:String,method:String="GET",body:JSONObject?=null):Request{
        val builder=Request.Builder().url(prefs.serverUrl+path).header("X-Eila-Token",prefs.pairingToken)
        if(method=="POST")builder.post((body?:JSONObject()).toString().toRequestBody(json))
        return builder.build()
    }

    fun post(path:String,body:JSONObject):JSONObject?=try{
        client.newCall(req(path,"POST",body)).execute().use{response->
            if(!response.isSuccessful)return null
            JSONObject(response.body?.string()?:"{}")
        }
    }catch(_:Exception){null}

    fun get(path:String):JSONObject?=try{
        client.newCall(req(path)).execute().use{response->
            if(!response.isSuccessful)return null
            JSONObject(response.body?.string()?:"{}")
        }
    }catch(_:Exception){null}

    private fun deviceKind():String=
        if(context.resources.configuration.smallestScreenWidthDp>=600)"tablet" else "phone"

    private fun hardwareFingerprint():String{
        val d=context.resources.displayMetrics
        return listOf(
            Build.MANUFACTURER,Build.MODEL,Build.DEVICE,Build.VERSION.SDK_INT.toString(),
            d.widthPixels.toString()+"x"+d.heightPixels.toString(),d.densityDpi.toString()
        ).joinToString("|")
    }

    fun heartbeat(state:JSONObject=JSONObject()):Boolean{
        val payload=JSONObject()
            .put("device_id",prefs.deviceId)
            .put("kind",deviceKind())
            .put("name",prefs.deviceName)
            .put("hardware_fingerprint",hardwareFingerprint())
            .put("capabilities",JSONObject()
                .put("camera",true)
                .put("gaze",true)
                .put("tts",true)
                .put("vibrate",true)
                .put("local_return",true)
                .put("snapshot_replica",true))
            .put("state",state)
        return post("/api/device/heartbeat",payload)!=null
    }

    fun sendGaze(payload:JSONObject):Boolean{
        payload.put("device_id",prefs.deviceId)
        return post("/api/gaze",payload)!=null
    }

    fun commands():JSONArray=
        get("/api/device/"+prefs.deviceId+"/commands")?.optJSONArray("commands")?:JSONArray()

    fun ack(id:Long){
        post("/api/device/"+prefs.deviceId+"/commands/"+id+"/ack",JSONObject())
    }
}
