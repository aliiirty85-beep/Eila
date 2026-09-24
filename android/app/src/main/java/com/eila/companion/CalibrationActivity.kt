package com.eila.companion

import android.os.Bundle
import android.graphics.Color
import android.view.Gravity
import android.widget.*
import androidx.appcompat.app.AppCompatActivity

class CalibrationActivity:AppCompatActivity(){
    private lateinit var model:CalibrationModel;private lateinit var root:FrameLayout;private lateinit var info:TextView;private lateinit var button:Button;private var index=0
    private data class T(val label:String,val x:Float,val y:Float,val text:String)
    private val targets=listOf(
        T("laptop",.1f,.1f,"بالا-راست صفحه لپ‌تاپ"),T("laptop",.5f,.1f,"بالا-وسط صفحه لپ‌تاپ"),T("laptop",.9f,.1f,"بالا-چپ صفحه لپ‌تاپ"),
        T("laptop",.1f,.5f,"وسط-راست صفحه لپ‌تاپ"),T("laptop",.5f,.5f,"مرکز صفحه لپ‌تاپ"),T("laptop",.9f,.5f,"وسط-چپ صفحه لپ‌تاپ"),
        T("laptop",.1f,.9f,"پایین-راست صفحه لپ‌تاپ"),T("laptop",.5f,.9f,"پایین-وسط صفحه لپ‌تاپ"),T("laptop",.9f,.9f,"پایین-چپ صفحه لپ‌تاپ"),
        T("book",.5f,.7f,"به محل معمول کتاب نگاه کن"),T("tablet",.5f,.5f,"به تبلت نگاه کن"),T("phone",.5f,.5f,"به محل معمول گوشی نگاه کن"),T("away",.5f,.5f,"به اطراف/دور از مطالعه نگاه کن")
    )
    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState);model=CalibrationModel(this);root=FrameLayout(this)
        info=TextView(this).apply{setTextColor(Color.WHITE);setBackgroundColor(Color.argb(180,0,0,0));textSize=20f;gravity=Gravity.CENTER;setPadding(20,20,20,20)}
        button=Button(this).apply{text="ثبت این نقطه"};root.setBackgroundColor(Color.BLACK);root.addView(info,FrameLayout.LayoutParams(-1,-2,Gravity.TOP));root.addView(button,FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM));setContentView(root);button.setOnClickListener{capture()};showTarget()
    }
    private fun showTarget(){if(index>=targets.size){info.text="کالیبراسیون تمام شد. ${model.count()} نمونه ذخیره شد.";button.text="بستن";button.setOnClickListener{finish()};return};val t=targets[index];info.text="مرحله ${index+1}/${targets.size}: ${t.text}\n۲ ثانیه ثابت نگاه کن، سپس ثبت را بزن."}
    private fun capture(){val t=targets[index];val samples=GazeRuntime.recent(16);if(samples.size<4){Toast.makeText(this,"هنوز نمونه کافی از دوربین ندارم؛ چند ثانیه صبر کن.",Toast.LENGTH_SHORT).show();return};model.addSamples(t.label,t.x,t.y,samples);index++;showTarget()}
}
