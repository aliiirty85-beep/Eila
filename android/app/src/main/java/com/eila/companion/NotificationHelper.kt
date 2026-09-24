package com.eila.companion

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat

object NotificationHelper{
    const val CHANNEL="eila_main";const val SERVICE_ID=1401
    fun ensure(context:Context){val nm=context.getSystemService(NotificationManager::class.java);nm.createNotificationChannel(NotificationChannel(CHANNEL,"Eila",NotificationManager.IMPORTANCE_HIGH))}
    fun notification(context:Context,title:String,text:String,ongoing:Boolean=false)=NotificationCompat.Builder(context,CHANNEL)
        .setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle(title).setContentText(text).setStyle(NotificationCompat.BigTextStyle().bigText(text)).setOngoing(ongoing).setPriority(NotificationCompat.PRIORITY_HIGH)
        .setContentIntent(PendingIntent.getActivity(context,0,Intent(context,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)).build()
    fun show(context:Context,id:Int,title:String,text:String){ensure(context);context.getSystemService(NotificationManager::class.java).notify(id,notification(context,title,text,false))}
}
