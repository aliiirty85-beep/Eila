package com.eila.ballrival

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

object EilaBridge{
    private val io=Executors.newSingleThreadExecutor()
    fun event(cfg:OverlayConfig,event:String,extra:JSONObject=JSONObject()){
        if(!cfg.eilaEnabled||cfg.eilaUrl.isBlank())return
        io.execute{
            try{
                val c=(URL(cfg.eilaUrl.trim().trimEnd('/')+"/api/stimulus/ball").openConnection() as HttpURLConnection).apply{
                    requestMethod="POST";connectTimeout=2500;readTimeout=3000;doOutput=true
                    setRequestProperty("Content-Type","application/json; charset=utf-8")
                    if(cfg.eilaToken.isNotBlank())setRequestProperty("X-Eila-Token",cfg.eilaToken.trim())
                }
                val body=JSONObject().put("source","BallRivalAndroid").put("event",event).put("ts",System.currentTimeMillis()).put("extra",extra).toString().toByteArray()
                c.outputStream.use{it.write(body)}
                runCatching{c.inputStream.close()}
                c.disconnect()
            }catch(_:Exception){}
        }
    }
}
