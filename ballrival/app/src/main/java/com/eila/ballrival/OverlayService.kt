package com.eila.ballrival

import android.app.*
import android.content.*
import android.content.res.Configuration
import android.graphics.PixelFormat
import android.graphics.Rect
import android.os.*
import android.provider.Settings
import android.view.*
import org.json.JSONObject
import kotlin.random.Random

class OverlayService:Service(){
    companion object{
        const val ACTION_PATTERN="ballrival.pattern"
        const val ACTION_PAUSE="ballrival.pause"
        const val ACTION_STOP="ballrival.stop"
    }
    private lateinit var wm:WindowManager
    private val handler=Handler(Looper.getMainLooper())
    private data class Rival(val view:BallView,val params:WindowManager.LayoutParams,var move:Runnable?=null)
    private val rivals=mutableListOf<Rival>()
    private var cfg=OverlayBus.config.copy()
    private var paused=false
    private var countTask:Runnable?=null
    private var taps=0
    private var moves=0

    override fun onCreate(){
        super.onCreate();OverlayBus.service=this;wm=getSystemService(Context.WINDOW_SERVICE) as WindowManager
        createChannel();startForeground(77,notification())
        if(Settings.canDrawOverlays(this))restartPattern()
    }

    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int{
        when(intent?.action){
            ACTION_PATTERN->newPattern()
            ACTION_PAUSE->togglePause()
            ACTION_STOP->{stopSelf();return START_NOT_STICKY}
            else->if(Settings.canDrawOverlays(this)){if(rivals.isEmpty())restartPattern() else applyConfig()}
        }
        return START_STICKY
    }

    override fun onConfigurationChanged(newConfig:Configuration){
        super.onConfigurationChanged(newConfig)
        rivals.forEach{r->randomize(r,false);runCatching{wm.updateViewLayout(r.view,r.params)}}
    }

    private fun isTablet()=resources.configuration.smallestScreenWidthDp>=600
    private fun px(dp:Int):Int{
        val boost=if(cfg.tabletBoost&&isTablet())1.18f else 1f
        return (dp*boost*resources.displayMetrics.density).toInt().coerceAtLeast(1)
    }
    private fun ri(a:Int,b:Int)=if(a>=b)a else Random.nextInt(a,b+1)
    private fun rl(a:Long,b:Long)=if(a>=b)a else Random.nextLong(a,b+1)
    private fun type()=if(Build.VERSION.SDK_INT>=26)WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY else @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

    private fun safeBounds():Rect{
        return if(Build.VERSION.SDK_INT>=30){
            val m=wm.currentWindowMetrics
            val i=m.windowInsets.getInsetsIgnoringVisibility(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            Rect(m.bounds.left+i.left,m.bounds.top+i.top,m.bounds.right-i.right,m.bounds.bottom-i.bottom)
        }else{
            @Suppress("DEPRECATION")
            val d=resources.displayMetrics;Rect(0,0,d.widthPixels,d.heightPixels)
        }
    }

    private fun normalize(){
        cfg.minBalls=cfg.minBalls.coerceIn(1,20);cfg.maxBalls=cfg.maxBalls.coerceIn(cfg.minBalls,20)
        cfg.minSizeDp=cfg.minSizeDp.coerceIn(24,360);cfg.maxSizeDp=cfg.maxSizeDp.coerceIn(cfg.minSizeDp,360)
        cfg.minStayMs=cfg.minStayMs.coerceIn(500,30000);cfg.maxStayMs=cfg.maxStayMs.coerceIn(cfg.minStayMs,30000)
        cfg.minOpacity=cfg.minOpacity.coerceIn(10,100);cfg.maxOpacity=cfg.maxOpacity.coerceIn(cfg.minOpacity,100)
    }

    private fun makeBall(){
        val s=px(ri(cfg.minSizeDp,cfg.maxSizeDp))
        val p=WindowManager.LayoutParams(s,s,type(),WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,PixelFormat.TRANSLUCENT).apply{gravity=Gravity.TOP or Gravity.START}
        lateinit var r:Rival
        val v=BallView(this,{destroyBall(r,true)},{cfg.tapDestroys})
        r=Rival(v,p);randomize(r,true);wm.addView(v,p);rivals.add(r);scheduleMove(r)
    }

    private fun randomize(r:Rival,resize:Boolean){
        if(resize){val s=px(ri(cfg.minSizeDp,cfg.maxSizeDp));r.params.width=s;r.params.height=s}
        val b=safeBounds();val maxX=(b.right-r.params.width).coerceAtLeast(b.left);val maxY=(b.bottom-r.params.height).coerceAtLeast(b.top)
        r.params.x=if(maxX>b.left)ri(b.left,maxX) else b.left
        r.params.y=if(maxY>b.top)ri(b.top,maxY) else b.top
        r.view.opacityPercent=ri(cfg.minOpacity,cfg.maxOpacity)
    }

    private fun scheduleMove(r:Rival){
        r.move?.let(handler::removeCallbacks);if(paused)return
        val task=Runnable{
            if(rivals.contains(r)&&!paused){
                randomize(r,true);moves++;runCatching{wm.updateViewLayout(r.view,r.params)};scheduleMove(r)
            }
        }
        r.move=task;handler.postDelayed(task,rl(cfg.minStayMs,cfg.maxStayMs))
    }

    private fun destroyBall(r:Rival,byTap:Boolean=false){
        r.move?.let(handler::removeCallbacks)
        if(!rivals.remove(r))return
        if(byTap){
            taps++
            EilaBridge.event(cfg,"tap",JSONObject().put("taps",taps).put("moves",moves).put("balls_before",rivals.size+1))
            r.view.animate().alpha(0f).setDuration(150).withEndAction{runCatching{wm.removeView(r.view)}}.start()
        }else runCatching{wm.removeView(r.view)}
    }

    private fun setCount(){
        val target=ri(cfg.minBalls,cfg.maxBalls)
        while(rivals.size<target)makeBall()
        while(rivals.size>target)destroyBall(rivals.last())
    }

    private fun scheduleCount(){
        countTask?.let(handler::removeCallbacks);if(paused)return
        val t=Runnable{if(!paused){setCount();scheduleCount()}}
        countTask=t;handler.postDelayed(t,rl(5000,8000))
    }

    private fun clear(){
        countTask?.let(handler::removeCallbacks);countTask=null
        rivals.toList().forEach{destroyBall(it)}
    }

    private fun restartPattern(){
        clear();cfg=OverlayBus.config.copy();normalize();taps=0;moves=0;setCount();scheduleCount()
        EilaBridge.event(cfg,"pattern",JSONObject().put("tablet",isTablet()).put("minBalls",cfg.minBalls).put("maxBalls",cfg.maxBalls))
    }

    fun applyConfig(){cfg=OverlayBus.config.copy();normalize();setCount();rivals.forEach{randomize(it,true);runCatching{wm.updateViewLayout(it.view,it.params)};scheduleMove(it)};scheduleCount();EilaBridge.event(cfg,"config_applied")}
    fun newPattern(){restartPattern()}
    fun togglePause(){
        paused=!paused
        if(paused){countTask?.let(handler::removeCallbacks);rivals.forEach{it.move?.let(handler::removeCallbacks)};EilaBridge.event(cfg,"pause")}
        else{rivals.forEach(::scheduleMove);scheduleCount();EilaBridge.event(cfg,"resume")}
        startForeground(77,notification())
    }

    private fun pending(action:String,id:Int)=PendingIntent.getService(this,id,Intent(this,OverlayService::class.java).setAction(action),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    private fun createChannel(){if(Build.VERSION.SDK_INT>=26)getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel("overlay","Ball Rival",NotificationManager.IMPORTANCE_LOW))}
    private fun notification():Notification{
        val open=PendingIntent.getActivity(this,0,Intent(this,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val b=if(Build.VERSION.SDK_INT>=26)Notification.Builder(this,"overlay") else @Suppress("DEPRECATION") Notification.Builder(this)
        return b.setContentTitle(if(paused)"Ball Rival — paused" else "Ball Rival is running")
            .setContentText("Phone + tablet • event-driven")
            .setSmallIcon(android.R.drawable.ic_menu_view).setContentIntent(open).setOngoing(true)
            .addAction(Notification.Action.Builder(null,if(paused)"Resume" else "Pause",pending(ACTION_PAUSE,2)).build())
            .addAction(Notification.Action.Builder(null,"Attack Now",pending(ACTION_PATTERN,3)).build())
            .addAction(Notification.Action.Builder(null,"Stop",pending(ACTION_STOP,4)).build()).build()
    }

    override fun onDestroy(){EilaBridge.event(cfg,"stop",JSONObject().put("taps",taps).put("moves",moves));clear();OverlayBus.service=null;super.onDestroy()}
    override fun onBind(intent:Intent?):IBinder?=null
}
