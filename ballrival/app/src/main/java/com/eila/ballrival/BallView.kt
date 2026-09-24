package com.eila.ballrival

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.MotionEvent
import android.view.View
import kotlin.math.min

class BallView(context:Context,private val destroy:()->Unit,private val canDestroy:()->Boolean):View(context){
    private val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply{color=Color.rgb(100,149,237)}
    var opacityPercent:Int=100
        set(v){field=v.coerceIn(0,100);invalidate()}
    init{setWillNotDraw(false);isClickable=true}
    override fun onDraw(c:Canvas){
        super.onDraw(c)
        paint.alpha=(255f*opacityPercent/100f).toInt().coerceIn(0,255)
        val r=min(width,height)/2f
        c.drawCircle(width/2f,height/2f,r,paint)
    }
    override fun onTouchEvent(e:MotionEvent):Boolean{
        val dx=e.x-width/2f;val dy=e.y-height/2f;val r=min(width,height)/2f
        if(dx*dx+dy*dy>r*r)return false
        if(e.action==MotionEvent.ACTION_UP){performClick();if(canDestroy())destroy()}
        return true
    }
    override fun performClick():Boolean{super.performClick();return true}
}
