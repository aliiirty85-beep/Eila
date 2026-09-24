package com.eila.ballrival

import android.Manifest
import android.content.*
import android.content.pm.PackageManager
import android.net.Uri
import android.os.*
import android.provider.Settings
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity:AppCompatActivity(){
    private lateinit var minCount:SeekBar;private lateinit var maxCount:SeekBar;private lateinit var minSize:SeekBar;private lateinit var maxSize:SeekBar
    private lateinit var minStay:SeekBar;private lateinit var maxStay:SeekBar;private lateinit var minOpacity:SeekBar;private lateinit var maxOpacity:SeekBar
    private lateinit var countLabel:TextView;private lateinit var sizeLabel:TextView;private lateinit var stayLabel:TextView;private lateinit var opacityLabel:TextView;private lateinit var status:TextView
    private lateinit var tapDestroys:CheckBox;private lateinit var tabletBoost:CheckBox;private lateinit var eilaEnabled:CheckBox
    private lateinit var eilaUrl:EditText;private lateinit var eilaToken:EditText
    private val prefs by lazy{getSharedPreferences("ball_rival",MODE_PRIVATE)}

    override fun onCreate(b:Bundle?){
        super.onCreate(b);setContentView(R.layout.activity_main)
        minCount=findViewById(R.id.minCount);maxCount=findViewById(R.id.maxCount);minSize=findViewById(R.id.minSize);maxSize=findViewById(R.id.maxSize)
        minStay=findViewById(R.id.minStay);maxStay=findViewById(R.id.maxStay);minOpacity=findViewById(R.id.minOpacity);maxOpacity=findViewById(R.id.maxOpacity)
        countLabel=findViewById(R.id.countLabel);sizeLabel=findViewById(R.id.sizeLabel);stayLabel=findViewById(R.id.stayLabel);opacityLabel=findViewById(R.id.opacityLabel);status=findViewById(R.id.status)
        tapDestroys=findViewById(R.id.tapDestroys);tabletBoost=findViewById(R.id.tabletBoost);eilaEnabled=findViewById(R.id.eilaEnabled);eilaUrl=findViewById(R.id.eilaUrl);eilaToken=findViewById(R.id.eilaToken)
        load()
        val l=object:SeekBar.OnSeekBarChangeListener{
            override fun onProgressChanged(s:SeekBar?,p:Int,f:Boolean){fix(s);labels();if(f){readConfig();save();OverlayBus.service?.applyConfig()}}
            override fun onStartTrackingTouch(s:SeekBar?){}
            override fun onStopTrackingTouch(s:SeekBar?){}
        }
        listOf(minCount,maxCount,minSize,maxSize,minStay,maxStay,minOpacity,maxOpacity).forEach{it.setOnSeekBarChangeListener(l)}
        val checks=CompoundButton.OnCheckedChangeListener{_,_->readConfig();save();OverlayBus.service?.applyConfig()}
        tapDestroys.setOnCheckedChangeListener(checks);tabletBoost.setOnCheckedChangeListener(checks);eilaEnabled.setOnCheckedChangeListener(checks)
        labels()
        findViewById<Button>(R.id.start).setOnClickListener{readConfig();save();startOverlay()}
        findViewById<Button>(R.id.pattern).setOnClickListener{OverlayBus.service?.newPattern()}
        findViewById<Button>(R.id.pause).setOnClickListener{OverlayBus.service?.togglePause()}
        findViewById<Button>(R.id.stop).setOnClickListener{stopService(Intent(this,OverlayService::class.java));status.text="Overlay stopped"}
    }

    private fun load(){
        val tablet=resources.configuration.smallestScreenWidthDp>=600
        minCount.progress=prefs.getInt("minCount",2);maxCount.progress=prefs.getInt("maxCount",6)
        minSize.progress=prefs.getInt("minSize",if(tablet)80 else 50);maxSize.progress=prefs.getInt("maxSize",if(tablet)170 else 130)
        minStay.progress=prefs.getInt("minStay",0);maxStay.progress=prefs.getInt("maxStay",7)
        minOpacity.progress=prefs.getInt("minOpacity",45);maxOpacity.progress=prefs.getInt("maxOpacity",100)
        tapDestroys.isChecked=prefs.getBoolean("tapDestroys",true);tabletBoost.isChecked=prefs.getBoolean("tabletBoost",true)
        eilaEnabled.isChecked=prefs.getBoolean("eilaEnabled",false);eilaUrl.setText(prefs.getString("eilaUrl",""));eilaToken.setText(prefs.getString("eilaToken",""))
    }

    private fun save(){
        prefs.edit().putInt("minCount",minCount.progress).putInt("maxCount",maxCount.progress).putInt("minSize",minSize.progress).putInt("maxSize",maxSize.progress)
            .putInt("minStay",minStay.progress).putInt("maxStay",maxStay.progress).putInt("minOpacity",minOpacity.progress).putInt("maxOpacity",maxOpacity.progress)
            .putBoolean("tapDestroys",tapDestroys.isChecked).putBoolean("tabletBoost",tabletBoost.isChecked).putBoolean("eilaEnabled",eilaEnabled.isChecked)
            .putString("eilaUrl",eilaUrl.text.toString()).putString("eilaToken",eilaToken.text.toString()).apply()
    }

    private fun fix(s:SeekBar?){
        if(s===minCount&&minCount.progress>maxCount.progress)maxCount.progress=minCount.progress;if(s===maxCount&&maxCount.progress<minCount.progress)minCount.progress=maxCount.progress
        if(s===minSize&&minSize.progress>maxSize.progress)maxSize.progress=minSize.progress;if(s===maxSize&&maxSize.progress<minSize.progress)minSize.progress=maxSize.progress
        if(s===minStay&&minStay.progress>maxStay.progress)maxStay.progress=minStay.progress;if(s===maxStay&&maxStay.progress<minStay.progress)minStay.progress=maxStay.progress
        if(s===minOpacity&&minOpacity.progress>maxOpacity.progress)maxOpacity.progress=minOpacity.progress;if(s===maxOpacity&&maxOpacity.progress<minOpacity.progress)minOpacity.progress=maxOpacity.progress
    }

    private fun readConfig(){
        OverlayBus.config=OverlayConfig(minCount.progress+1,maxCount.progress+1,minSize.progress+24,maxSize.progress+24,(minStay.progress+1)*1000L,(maxStay.progress+1)*1000L,
            minOpacity.progress.coerceAtLeast(10),maxOpacity.progress.coerceAtLeast(10),tapDestroys.isChecked,tabletBoost.isChecked,eilaEnabled.isChecked,eilaUrl.text.toString().trim(),eilaToken.text.toString().trim())
    }

    private fun labels(){
        countLabel.text="Balls: "+(minCount.progress+1)+" – "+(maxCount.progress+1)
        sizeLabel.text="Ball size: "+(minSize.progress+24)+" – "+(maxSize.progress+24)+" dp"
        stayLabel.text="Stay: "+(minStay.progress+1)+" – "+(maxStay.progress+1)+" sec"
        opacityLabel.text="Opacity: "+minOpacity.progress.coerceAtLeast(10)+"% – "+maxOpacity.progress.coerceAtLeast(10)+"%"
    }

    private fun startOverlay(){
        if(!Settings.canDrawOverlays(this)){status.text="Enable Display over other apps, then return";startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+packageName)));return}
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),44)
        ContextCompat.startForegroundService(this,Intent(this,OverlayService::class.java))
        status.text=if(resources.configuration.smallestScreenWidthDp>=600)"Overlay running — tablet mode" else "Overlay running"
    }
    override fun onResume(){super.onResume();if(Settings.canDrawOverlays(this))status.text="Overlay permission ready"}
}
