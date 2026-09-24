package com.eila.companion

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.app.NotificationManager
import org.json.JSONObject

class ReturnActionReceiver:BroadcastReceiver(){
    override fun onReceive(context:Context,intent:Intent){
        val id=intent.getLongExtra("contract_id",-1L);if(id<0)return
        LocalStore(context).finishReturn(id);context.getSystemService(NotificationManager::class.java).cancel(2600+(id%50).toInt())
        val pending=goAsync()
        Thread{try{EilaApi(context).post("/api/return/ack",JSONObject().put("contract_id",id))}finally{pending.finish()}}.start()
    }
}