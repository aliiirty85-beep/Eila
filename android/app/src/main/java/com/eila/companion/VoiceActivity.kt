package com.eila.companion

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import android.view.Gravity
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject
import java.util.Locale

class VoiceActivity:AppCompatActivity(),TextToSpeech.OnInitListener{
    private lateinit var status:TextView
    private var tts:TextToSpeech?=null
    private val listen=registerForActivityResult(ActivityResultContracts.StartActivityForResult()){r->
        if(r.resultCode==Activity.RESULT_OK){
            val words=r.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            val text=words?.firstOrNull()
            if(!text.isNullOrBlank())send(text) else status.text="چیزی نشنیدم."
        }else status.text="شنیدن لغو شد."
    }
    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState);tts=TextToSpeech(this,this)
        val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(32,32,32,32);gravity=Gravity.CENTER}
        status=TextView(this).apply{text="حرف بزن؛ ایلا پاسخ کوتاه می‌دهد.";textSize=20f;gravity=Gravity.CENTER}
        val b=Button(this).apply{text="شروع صحبت"};root.addView(status,LinearLayout.LayoutParams(-1,-2));root.addView(b,LinearLayout.LayoutParams(-1,-2));setContentView(root)
        b.setOnClickListener{startListening()}
    }
    private fun startListening(){
        try{
            val i=Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM).putExtra(RecognizerIntent.EXTRA_LANGUAGE,"fa-IR").putExtra(RecognizerIntent.EXTRA_PROMPT,"با ایلا صحبت کن")
            listen.launch(i)
        }catch(e:Exception){status.text="موتور تشخیص گفتار روی این دستگاه در دسترس نیست."}
    }
    private fun send(text:String){
        status.text="تو: "+text+"\n\nایلا در حال فکر کردن…"
        Thread{
            val r=EilaApi(this).post("/api/chat",JSONObject().put("message",text));val answer=r?.optString("text")?:"ارتباط با مغز ایلا برقرار نشد."
            runOnUiThread{status.text="تو: "+text+"\n\nایلا: "+answer;tts?.speak(answer,TextToSpeech.QUEUE_FLUSH,null,"eila-voice")}
        }.start()
    }
    override fun onInit(statusCode:Int){if(statusCode==TextToSpeech.SUCCESS){tts?.language=Locale("fa","IR");tts?.setSpeechRate(.95f)}}
    override fun onDestroy(){tts?.stop();tts?.shutdown();super.onDestroy()}
}
