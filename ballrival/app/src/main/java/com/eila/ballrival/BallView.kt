package com.eila.ballrival

import android.content.Context
import android.graphics.*
import android.view.*
import kotlin.math.min

class BallView(context:Context,private val destroy:()->Unit,private val canDestroy:()->Boolean):View(context){
    private val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply{color=Color.rgb(100,149,237)}
    private val insetListener=ViewTreeObserver.OnComputeInternalInsetsListener{info->
        info.setTouchableInsets(ViewTreeObserver.InternalInsetsInfo.TOUCHABLE_INSETS_REGION)
        val path=Path().apply{addCircle(width/2f,height/2f,min(width,height)/2f,Path.Direction.CW)}
        val clip=Region(0,0,width,height);val region=Region();region.setPath(path,clip);info.touchableRegion.set(region)
    }
    var opacityPercent:Int=100
        set(v){field=v.coerceIn(0,100);invalidate()}
    init{setWillNotDraw(false);isClickable=true}
    override fun onAttachedToWindow(){super.onAttachedToWindow();viewTreeObserver.addOnComputeInternalInsetsListener(insetListener)}
    override fun onDetachedFromWindow(){if(viewTreeObserver.isAlive)viewTreeObserver.removeOnComputeInternalInsetsListener(insetListener);super.onDetachedFromWindow()}
    override fun onDraw(c:Canvas){super.onDraw(c);paint.alpha=(255f*opacityPercent/100f).toInt();val r=min(width,height)/2f;c.drawCircle(width/2f,height/2f,r,paint)}
    override fun onTouchEvent(e:MotionEvent):Boolean{
        val dx=e.x-width/2f;val dy=e.y-height/2f;val r=min(width,height)/2f
        if(dx*dx+dy*dy>r*r)return false
        if(e.action==MotionEvent.ACTION_UP){performClick();if(canDestroy())destroy()}
        return true
    }
    override fun performClick():Boolean{super.performClick();return true}
}
