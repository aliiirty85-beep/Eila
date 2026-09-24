package com.eila.companion

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity:AppCompatActivity(){
    private lateinit var prefs:AppPrefs
    private var afterPermission:(()->Unit)?=null
    private val askPermissions=registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()){result->
        val camera=result[Manifest.permission.CAMERA] ?: (ContextCompat.checkSelfPermission(this,Manifest.permission.CAMERA)==PackageManager.PERMISSION_GRANTED)
        if(camera){afterPermission?.invoke()}else Toast.makeText(this,"برای Gaze/عکس صفحه، دسترسی دوربین لازم است.",Toast.LENGTH_LONG).show()
        afterPermission=null
    }

    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState);prefs=AppPrefs(this);NotificationHelper.ensure(this)
        val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(32,32,32,32);gravity=Gravity.CENTER_HORIZONTAL}
        fun input(hint:String,value:String)=EditText(this).apply{this.hint=hint;setText(value)}
        val title=TextView(this).apply{text="Eila Companion 2.0 LTS";textSize=25f;gravity=Gravity.CENTER}
        val server=input("http://IP-LAPTOP:8765",prefs.serverUrl);val token=input("Pairing token",prefs.pairingToken);val name=input("نام دستگاه",prefs.deviceName)
        val status=TextView(this).apply{text="سرویس دوربین را از همین صفحه شروع کن. هر دستگاه کالیبراسیون جدا دارد."}
        val save=Button(this).apply{text="ذخیره اتصال"};val start=Button(this).apply{text="شروع ایلا / Gaze"};val stop=Button(this).apply{text="توقف Gaze"}
        val cal=Button(this).apply{text="کالیبراسیون شخصی Gaze"};val page=Button(this).apply{text="عکس صفحه کتاب / منبع فعال"};val voice=Button(this).apply{text="صحبت با ایلا"}
        listOf(title,server,token,name,save,start,stop,cal,page,voice,status).forEach{root.addView(it,LinearLayout.LayoutParams(-1,-2).apply{setMargins(0,9,0,9)})};setContentView(root)
        save.setOnClickListener{prefs.serverUrl=server.text.toString();prefs.pairingToken=token.text.toString();prefs.deviceName=name.text.toString();Toast.makeText(this,"ذخیره شد",Toast.LENGTH_SHORT).show()}
        start.setOnClickListener{save.performClick();withCamera{ContextCompat.startForegroundService(this,Intent(this,GazeService::class.java));status.text="ایلا فعال شد. اعلان دائمی باید دیده شود."}}
        stop.setOnClickListener{stopService(Intent(this,GazeService::class.java));status.text="Gaze متوقف شد."}
        cal.setOnClickListener{withCamera{ContextCompat.startForegroundService(this,Intent(this,GazeService::class.java));startActivity(Intent(this,CalibrationActivity::class.java))}}
        page.setOnClickListener{save.performClick();withCamera{startActivity(Intent(this,PageCaptureActivity::class.java))}}
        voice.setOnClickListener{save.performClick();startActivity(Intent(this,VoiceActivity::class.java))}
    }

    private fun withCamera(action:()->Unit){
        val cameraOk=ContextCompat.checkSelfPermission(this,Manifest.permission.CAMERA)==PackageManager.PERMISSION_GRANTED
        if(cameraOk){requestNotificationsIfNeeded();action();return}
        afterPermission={requestNotificationsIfNeeded();action()}
        val needed=mutableListOf(Manifest.permission.CAMERA)
        if(Build.VERSION.SDK_INT>=33 && ContextCompat.checkSelfPermission(this,Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)needed+=Manifest.permission.POST_NOTIFICATIONS
        askPermissions.launch(needed.toTypedArray())
    }

    private fun requestNotificationsIfNeeded(){
        if(Build.VERSION.SDK_INT>=33 && ContextCompat.checkSelfPermission(this,Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){
            askPermissions.launch(arrayOf(Manifest.permission.POST_NOTIFICATIONS))
        }
    }
}
