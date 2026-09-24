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
    private val askPermissions=registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()){}
    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState);prefs=AppPrefs(this);NotificationHelper.ensure(this)
        val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(32,32,32,32);gravity=Gravity.CENTER_HORIZONTAL}
        fun input(hint:String,value:String)=EditText(this).apply{this.hint=hint;setText(value)}
        val title=TextView(this).apply{text="Eila Companion 2.0 LTS";textSize=25f;gravity=Gravity.CENTER}
        val server=input("http://IP-LAPTOP:8765",prefs.serverUrl);val token=input("Pairing token",prefs.pairingToken);val name=input("نام دستگاه",prefs.deviceName)
        val status=TextView(this).apply{text="نکته: سرویس دوربین را باید از همین صفحه شروع کنی."}
        val save=Button(this).apply{text="ذخیره اتصال"};val start=Button(this).apply{text="شروع ایلا / Gaze"};val stop=Button(this).apply{text="توقف Gaze"};val cal=Button(this).apply{text="کالیبراسیون شخصی Gaze"}
        listOf(title,server,token,name,save,start,stop,cal,status).forEach{root.addView(it,LinearLayout.LayoutParams(-1,-2).apply{setMargins(0,10,0,10)})};setContentView(root)
        save.setOnClickListener{prefs.serverUrl=server.text.toString();prefs.pairingToken=token.text.toString();prefs.deviceName=name.text.toString();Toast.makeText(this,"ذخیره شد",Toast.LENGTH_SHORT).show()}
        start.setOnClickListener{save.performClick();requestNeeded();ContextCompat.startForegroundService(this,Intent(this,GazeService::class.java));status.text="ایلا فعال شد. اعلان دائمی باید دیده شود."}
        stop.setOnClickListener{stopService(Intent(this,GazeService::class.java));status.text="Gaze متوقف شد."}
        cal.setOnClickListener{requestNeeded();ContextCompat.startForegroundService(this,Intent(this,GazeService::class.java));startActivity(Intent(this,CalibrationActivity::class.java))}
    }
    private fun requestNeeded(){val p=mutableListOf(Manifest.permission.CAMERA);if(Build.VERSION.SDK_INT>=33)p+=Manifest.permission.POST_NOTIFICATIONS;val miss=p.filter{ContextCompat.checkSelfPermission(this,it)!=PackageManager.PERMISSION_GRANTED};if(miss.isNotEmpty())askPermissions.launch(miss.toTypedArray())}
}
