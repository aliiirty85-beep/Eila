package com.eila.companion

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.Build
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.speech.tts.TextToSpeech
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleService
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.facelandmarker.FaceLandmarker
import kotlinx.coroutines.*
import org.json.JSONObject
import java.util.Locale
import java.util.concurrent.Executors

class GazeService:LifecycleService(),TextToSpeech.OnInitListener{
    private val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO);private val cameraExecutor=Executors.newSingleThreadExecutor()
    private lateinit var prefs:AppPrefs;private lateinit var api:EilaApi;private lateinit var local:LocalStore;private lateinit var calibration:CalibrationModel;private lateinit var metrics:GazeMetrics
    private var landmarker:FaceLandmarker?=null;private var tts:TextToSpeech?=null;private var lastFrameAt=0L;private var lastGazeSendAt=0L;private var lastHeartbeat=0L;private var lastSync=0L;private var lastOfflineGuard=0L
    @Volatile private var serverOnline=true
    private var latestPrediction=GazePrediction("unknown",null,null,0f)

    override fun onCreate(){super.onCreate();prefs=AppPrefs(this);api=EilaApi(this);local=LocalStore(this);calibration=CalibrationModel(this);metrics=GazeMetrics();tts=TextToSpeech(this,this);NotificationHelper.ensure(this);startForeground(NotificationHelper.SERVICE_ID,NotificationHelper.notification(this,"ایلا فعال است","Gaze و پیگیری در حال اجراست",true));initLandmarker();startCamera();startNetworkLoop()}
    override fun onDestroy(){scope.cancel();cameraExecutor.shutdown();try{landmarker?.close()}catch(_:Exception){};tts?.stop();tts?.shutdown();super.onDestroy()}
    override fun onInit(status:Int){if(status==TextToSpeech.SUCCESS){tts?.language=Locale("fa","IR");tts?.setSpeechRate(.95f)}}

    private fun initLandmarker(){try{val base=BaseOptions.builder().setModelAssetPath("face_landmarker.task").build();val options=FaceLandmarker.FaceLandmarkerOptions.builder().setBaseOptions(base).setRunningMode(RunningMode.IMAGE).setNumFaces(1).setMinFaceDetectionConfidence(.5f).setMinFacePresenceConfidence(.5f).setMinTrackingConfidence(.5f).build();landmarker=FaceLandmarker.createFromOptions(this,options)}catch(e:Exception){NotificationHelper.show(this,1900,"ایلا","مدل Gaze بالا نیامد: \${e.javaClass.simpleName}")}}
    private fun startCamera(){val providerFuture=ProcessCameraProvider.getInstance(this);providerFuture.addListener({try{val provider=providerFuture.get();val analysis=ImageAnalysis.Builder().setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build();analysis.setAnalyzer(cameraExecutor){image->analyze(image)};provider.unbindAll();provider.bindToLifecycle(this,CameraSelector.DEFAULT_FRONT_CAMERA,analysis)}catch(e:Exception){NotificationHelper.show(this,1901,"ایلا","دوربین Gaze در دسترس نیست: \${e.javaClass.simpleName}")}},ContextCompat.getMainExecutor(this))}

    private fun analyze(image:ImageProxy){
        val now=SystemClock.elapsedRealtime();if(now-lastFrameAt<220){image.close();return};lastFrameAt=now
        try{
            val raw=image.toBitmap();val m=Matrix();m.postRotate(image.imageInfo.rotationDegrees.toFloat());m.postScale(-1f,1f);val bitmap=Bitmap.createBitmap(raw,0,0,raw.width,raw.height,m,true);val mp=BitmapImageBuilder(bitmap).build()
            val face=landmarker?.detect(mp)?.faceLandmarks()?.firstOrNull()
            if(face!=null&&face.size>473){
                fun p(i:Int)=face[i]
                val f=FeatureVector(listOf(p(468).x(),p(468).y(),p(473).x(),p(473).y(),p(1).x(),p(1).y(),p(33).x(),p(263).x(),p(10).y(),p(152).y()))
                GazeRuntime.push(f);val pred=calibration.predict(f);latestPrediction=pred;val met=metrics.add(pred);val event=(met["event"] as? String)?:""
                if(now-lastGazeSendAt>=800||event.isNotBlank()){lastGazeSendAt=now;val payload=JSONObject().put("zone",pred.zone).put("quality",pred.quality).put("timestamp_ms",System.currentTimeMillis());pred.x?.let{payload.put("x",it)};pred.y?.let{payload.put("y",it)};met.forEach{(k,value)->payload.put(k,value)};scope.launch{val ok=api.sendGaze(payload);serverOnline=ok;if(!ok)offlineGuard(met)}}else if(!serverOnline){offlineGuard(met)}
            }
        }catch(_:Exception){}finally{image.close()}
    }

    private fun offlineGuard(met:Map<String,Any?>){val now=System.currentTimeMillis();val micro=local.get("microgoal")?:"";if(micro.isBlank())return;val away=(met["away_streak_seconds"] as? Number)?.toFloat()?:0f;if(away>=8f&&now-lastOfflineGuard>=60_000){lastOfflineGuard=now;val text="ایلا آفلاینه، ولی نگهبانی فعاله. برگرد به مأموریت ذخیره‌شده.";speak(text);NotificationHelper.show(this,2500,"ایلا — حالت بقا",text)}}

    private fun startNetworkLoop(){scope.launch{while(isActive){val now=System.currentTimeMillis();if(now-lastHeartbeat>5000){serverOnline=api.heartbeat(JSONObject().put("calibration_points",calibration.count()).put("zone",latestPrediction.zone).put("offline_guard",true));lastHeartbeat=now};if(serverOnline){val a=api.commands();for(i in 0 until a.length()){val c=a.optJSONObject(i)?:continue;handleCommand(c);api.ack(c.optLong("id"))};if(now-lastSync>30_000){syncReplica();lastSync=now}};checkLocalReturns(now/1000);delay(2000)}}}

    private fun syncReplica(){val old=local.get("server_snapshot");if(!old.isNullOrBlank()){try{api.post("/api/sync/offer",JSONObject().put("device_id",prefs.deviceId).put("snapshot",JSONObject(old)))}catch(_:Exception){}};val fresh=api.get("/api/sync/snapshot");if(fresh!=null)local.put("server_snapshot",fresh.toString())}

    private fun handleCommand(c:JSONObject){val kind=c.optString("kind");val p=c.optJSONObject("payload")?:JSONObject();val text=p.optString("text");when(kind){
        "notify"->{if(text.isNotBlank())NotificationHelper.show(this,2000+(c.optLong("id")%500).toInt(),"ایلا",text)}
        "vibrate"->{vibrate();if(text.isNotBlank())NotificationHelper.show(this,2100,"ایلا",text)}
        "speak"->{if(text.isNotBlank()){speak(text);NotificationHelper.show(this,2200,"ایلا",text)}}
        "feedback"->{if(p.optBoolean("clear_microgoal",false))local.put("microgoal","");if(text.isNotBlank())NotificationHelper.show(this,2300,"ایلا",text)}
        "microgoal"->{val display=p.optString("display_instruction",p.optString("instruction"));local.put("microgoal",display);if(display.isNotBlank())NotificationHelper.show(this,2400,"مأموریت ایلا",display)}
        "clear_microgoal"->{local.put("microgoal","")}
        "schedule_return"->{local.saveReturn(p.optLong("contract_id"),p.optLong("due_at"),p.optString("text","برگشت به مطالعه"))}
        "return_ack"->{local.finishReturn(p.optLong("contract_id"))}
    }}

    private fun checkLocalReturns(nowSec:Long){val stages=listOf(0L,30L,90L,180L);local.pendingReturns().forEach{r->if(nowSec<r.dueAt)return@forEach;val overdue=nowSec-r.dueAt;var stage=-1;for(i in stages.indices)if(overdue>=stages[i])stage=i;if(stage<=r.lastStage)return@forEach;val text=when(stage){0->"ایلا: زمان برگشت رسید. برگرد سر مأموریت.";1->"ایلا: هنوز منتظرم. وقفه تمام شده.";2->"ایلا: برگشت عقب افتاده. همین الان برگرد.";else->"ایلا: وقفه دارد کش پیدا می‌کند. فقط یک micro-goal و تمام."};when(stage){0->NotificationHelper.showReturn(this,2600+(r.id%50).toInt(),r.id,text);1->{vibrate();NotificationHelper.showReturn(this,2600+(r.id%50).toInt(),r.id,text)};else->{speak(text);NotificationHelper.showReturn(this,2600+(r.id%50).toInt(),r.id,text)}};local.setReturnStage(r.id,stage)}}
    private fun speak(text:String){tts?.speak(text,TextToSpeech.QUEUE_FLUSH,null,"eila")}
    private fun vibrate(){val effect=VibrationEffect.createOneShot(500,VibrationEffect.DEFAULT_AMPLITUDE);if(Build.VERSION.SDK_INT>=31)getSystemService(VibratorManager::class.java).defaultVibrator.vibrate(effect)else @Suppress("DEPRECATION")(getSystemService(Context.VIBRATOR_SERVICE) as Vibrator).vibrate(effect)}
}