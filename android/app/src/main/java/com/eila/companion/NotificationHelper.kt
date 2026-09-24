package com.eila.companion

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat

object NotificationHelper{
    const val CHANNEL="eila_main";const val SERVICE_ID=1401
    fun ensure(context:Context){context.getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel(CHANNEL,"Eila",NotificationManager.IMPORTANCE_HIGH))}
    fun notification(context:Context,title:String,text:String,ongoing:Boolean=false)=NotificationCompat.Builder(context,CHANNEL)
        .setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle(title).setContentText(text)
        .setStyle(NotificationCompat.BigTextStyle().bigText(text)).setOngoing(ongoing).setPriority(NotificationCompat.PRIORITY_HIGH)
        .setContentIntent(PendingIntent.getActivity(context,0,Intent(context,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)).build()
    fun show(context:Context,id:Int,title:String,text:String){ensure(context);context.getSystemService(NotificationManager::class.java).notify(id,notification(context,title,text,false))}
    fun showReturn(context:Context,id:Int,contractId:Long,text:String){
        ensure(context)
        val action=Intent(context,ReturnActionReceiver::class.java).putExtra("contract_id",contractId)
        val pi=PendingIntent.getBroadcast(context,(contractId%Int.MAX_VALUE).toInt(),action,PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val n=NotificationCompat.Builder(context,CHANNEL).setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("ایلا منتظر برگشت توست").setContentText(text).setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setPriority(NotificationCompat.PRIORITY_HIGH).setAutoCancel(false).addAction(android.R.drawable.ic_menu_revert,"برگشتم",pi)
            .setContentIntent(PendingIntent.getActivity(context,1,Intent(context,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)).build()
        context.getSystemService(NotificationManager::class.java).notify(id,n)
    }
}