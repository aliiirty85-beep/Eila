package com.eila.companion

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Bundle
import android.provider.MediaStore
import android.util.Base64
import android.view.Gravity
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File

class PageCaptureActivity:AppCompatActivity(){
    private lateinit var file:File
    private lateinit var status:TextView
    private val capture=registerForActivityResult(ActivityResultContracts.StartActivityForResult()){r->
        if(r.resultCode==Activity.RESULT_OK)upload() else{status.text="عکس صفحه گرفته نشد.";restartGaze()}
    }
    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState)
        stopService(Intent(this,GazeService::class.java))
        val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(32,32,32,32);gravity=Gravity.CENTER}
        status=TextView(this).apply{text="یک عکس صاف و خوانا از صفحه کتاب بگیر. فقط همین تصویر به عنوان منبع فعال ایلا استفاده می‌شود.";textSize=19f;gravity=Gravity.CENTER}
        val b=Button(this).apply{text="باز کردن دوربین"};root.addView(status,LinearLayout.LayoutParams(-1,-2));root.addView(b,LinearLayout.LayoutParams(-1,-2));setContentView(root)
        b.setOnClickListener{openCamera()}
    }
    private fun openCamera(){
        try{
            val dir=File(cacheDir,"images").apply{mkdirs()};file=File(dir,"current_page.jpg")
            val uri=FileProvider.getUriForFile(this,"com.eila.companion.fileprovider",file)
            val i=Intent(MediaStore.ACTION_IMAGE_CAPTURE).putExtra(MediaStore.EXTRA_OUTPUT,uri).addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION or Intent.FLAG_GRANT_READ_URI_PERMISSION)
            capture.launch(i)
        }catch(e:Exception){status.text="دوربین سیستم در دسترس نیست."}
    }
    private fun upload(){
        status.text="در حال آماده‌سازی صفحه…"
        Thread{
            try{
                val src=BitmapFactory.decodeFile(file.absolutePath)?:throw IllegalStateException("decode")
                val maxW=1800
                val bmp=if(src.width>maxW){val h=(src.height*(maxW.toFloat()/src.width)).toInt();Bitmap.createScaledBitmap(src,maxW,h,true)}else src
                val out=ByteArrayOutputStream();bmp.compress(Bitmap.CompressFormat.JPEG,76,out);val data=Base64.encodeToString(out.toByteArray(),Base64.NO_WRAP)
                val r=EilaApi(this).post("/api/context/image",JSONObject().put("title","صفحه کتاب").put("data_url","data:image/jpeg;base64,"+data))
                runOnUiThread{status.text=if(r?.optBoolean("ok")==true)"صفحه ثبت شد ✓ حالا Gaze می‌تواند سؤال را به همین صفحه وصل کند.":"آپلود صفحه ناموفق بود؛ اتصال ایلا را بررسی کن.";restartGaze()}
            }catch(e:Exception){runOnUiThread{status.text="پردازش عکس ناموفق بود.";restartGaze()}}
        }.start()
    }
    private fun restartGaze(){try{ContextCompat.startForegroundService(this,Intent(this,GazeService::class.java))}catch(_:Exception){}}
}
