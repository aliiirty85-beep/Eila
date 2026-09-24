package com.eila.companion

import android.os.Bundle
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.*
import androidx.appcompat.app.AppCompatActivity

class CalibrationActivity:AppCompatActivity(){
    private lateinit var model:CalibrationModel;private lateinit var root:FrameLayout;private lateinit var info:TextView;private lateinit var button:Button
    private val handler=Handler(Looper.getMainLooper());private var index=0;private var running=false
    private data class T(val label:String,val x:Float,val y:Float,val text:String)
    private val targets=listOf(
        T("laptop",.1f,.1f,"به گوشه چپِ بالای صفحه لپ‌تاپ نگاه کن"),T("laptop",.5f,.1f,"به وسطِ بالای صفحه لپ‌تاپ نگاه کن"),T("laptop",.9f,.1f,"به گوشه راستِ بالای صفحه لپ‌تاپ نگاه کن"),
        T("laptop",.1f,.5f,"به وسطِ سمت چپ صفحه لپ‌تاپ نگاه کن"),T("laptop",.5f,.5f,"به مرکز صفحه لپ‌تاپ نگاه کن"),T("laptop",.9f,.5f,"به وسطِ سمت راست صفحه لپ‌تاپ نگاه کن"),
        T("laptop",.1f,.9f,"به گوشه چپِ پایین صفحه لپ‌تاپ نگاه کن"),T("laptop",.5f,.9f,"به وسطِ پایین صفحه لپ‌تاپ نگاه کن"),T("laptop",.9f,.9f,"به گوشه راستِ پایین صفحه لپ‌تاپ نگاه کن"),
        T("book",.5f,.7f,"به محل معمول کتابت نگاه کن"),T("tablet",.5f,.5f,"به محل معمول تبلت نگاه کن"),T("phone",.5f,.5f,"به خود صفحه گوشی نگاه کن"),T("away",.5f,.5f,"به نقطه‌ای دور از وسایل مطالعه نگاه کن"))
    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState);model=CalibrationModel(this);root=FrameLayout(this)
        info=TextView(this).apply{setTextColor(Color.WHITE);setBackgroundColor(Color.argb(190,0,0,0));textSize=20f;gravity=Gravity.CENTER;setPadding(24,24,24,24)}
        button=Button(this).apply{text="شروع کالیبراسیون خودکار"};root.setBackgroundColor(Color.BLACK);root.addView(info,FrameLayout.LayoutParams(-1,-2,Gravity.TOP));root.addView(button,FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM));setContentView(root)
        info.text="ایلا برای هر نقطه ۳ ثانیه فرصت می‌دهد. بعد خودش نمونه را ثبت می‌کند؛ هنگام ثبت به گوشی برنگرد."
        button.setOnClickListener{if(!running){model.clear();running=true;button.isEnabled=false;index=0;next()}}
    }
    private fun next(){
        if(index>=targets.size){running=false;info.text="کالیبراسیون تمام شد. \${model.count()} نمونه ذخیره شد.";button.isEnabled=true;button.text="بستن";button.setOnClickListener{finish()};return}
        val t=targets[index];info.text="مرحله \${index+1}/\${targets.size}\n\${t.text}\n\n۳…"
        handler.postDelayed({info.text="مرحله \${index+1}/\${targets.size}\n\${t.text}\n\n۲…"},1000)
        handler.postDelayed({info.text="مرحله \${index+1}/\${targets.size}\n\${t.text}\n\n۱…"},2000)
        handler.postDelayed({val samples=GazeRuntime.recent(12);if(samples.size>=4){model.addSamples(t.label,t.x,t.y,samples);index++;info.text="ثبت شد ✓";handler.postDelayed({next()},650)}else{info.text="نمونه دوربین کافی نیست؛ دوباره تلاش می‌کنم.";handler.postDelayed({next()},1500)}},3000)
    }
    override fun onDestroy(){handler.removeCallbacksAndMessages(null);super.onDestroy()}
}