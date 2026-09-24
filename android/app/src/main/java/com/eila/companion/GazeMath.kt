package com.eila.companion

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.min
import kotlin.math.sqrt

data class FeatureVector(val values:List<Float>)
data class CalibrationPoint(val label:String,val x:Float,val y:Float,val f:FeatureVector)
data class GazePrediction(val zone:String,val x:Float?,val y:Float?,val quality:Float)

object GazeRuntime{
    private val recent=ArrayDeque<FeatureVector>()
    @Synchronized fun push(f:FeatureVector){recent.addLast(f);while(recent.size>30)recent.removeFirst()}
    @Synchronized fun recent(n:Int=12):List<FeatureVector> = recent.takeLast(n)
}

class CalibrationModel(context:Context){
    private val prefs=context.getSharedPreferences("eila_calibration",Context.MODE_PRIVATE)
    private var points=load()
    fun count()=points.size
    fun clear(){points=mutableListOf();prefs.edit().remove("points").apply()}
    fun addSamples(label:String,x:Float,y:Float,features:List<FeatureVector>){features.forEach{points.add(CalibrationPoint(label,x,y,it))};save()}
    private fun dist(a:FeatureVector,b:FeatureVector):Double{val n=min(a.values.size,b.values.size);if(n==0)return 999.0;var s=0.0;for(i in 0 until n){val d=(a.values[i]-b.values[i]).toDouble();s+=d*d};return sqrt(s/n)}
    fun predict(f:FeatureVector):GazePrediction{
        if(points.size<6)return GazePrediction("unknown",null,null,0f)
        val ranked=points.map{it to dist(f,it.f)}.sortedBy{it.second}.take(12);val zoneScores=mutableMapOf<String,Double>()
        ranked.forEach{(p,d)->zoneScores[p.label]=(zoneScores[p.label]?:0.0)+1.0/(d+0.002)}
        val zone=zoneScores.maxByOrNull{it.value}?.key?:"unknown";val bestDist=ranked.firstOrNull()?.second?:1.0;val quality=(1.0/(1.0+bestDist*12.0)).toFloat().coerceIn(0f,1f)
        val screen=ranked.filter{it.first.label=="laptop"}
        if(screen.isEmpty()||zone!="laptop")return GazePrediction(zone,null,null,quality)
        var wx=0.0;var wy=0.0;var w=0.0
        screen.forEach{(p,d)->val q=1.0/(d*d+0.0001);wx+=p.x*q;wy+=p.y*q;w+=q}
        return GazePrediction(zone,(wx/w).toFloat().coerceIn(0f,1f),(wy/w).toFloat().coerceIn(0f,1f),quality)
    }
    private fun save(){val a=JSONArray();points.forEach{p->val o=JSONObject();o.put("label",p.label);o.put("x",p.x);o.put("y",p.y);val fa=JSONArray();p.f.values.forEach{fa.put(it.toDouble())};o.put("f",fa);a.put(o)};prefs.edit().putString("points",a.toString()).apply()}
    private fun load():MutableList<CalibrationPoint>{val out=mutableListOf<CalibrationPoint>();val raw=prefs.getString("points","[]")?:"[]";try{val a=JSONArray(raw);for(i in 0 until a.length()){val o=a.getJSONObject(i);val fa=o.getJSONArray("f");val fv=mutableListOf<Float>();for(j in 0 until fa.length())fv+=fa.getDouble(j).toFloat();out+=CalibrationPoint(o.getString("label"),o.getDouble("x").toFloat(),o.getDouble("y").toFloat(),FeatureVector(fv))}}catch(_:Exception){};return out}
}

class GazeMetrics{
    private data class S(val t:Long,val p:GazePrediction)
    private val h=ArrayDeque<S>();private var fixationStart=0L;private var fixationX:Float?=null;private var fixationY:Float?=null;private var fixationZone="";private var lastEventAt=0L
    fun add(p:GazePrediction):Map<String,Any?>{
        val now=System.currentTimeMillis();h.addLast(S(now,p));while(h.isNotEmpty()&&now-h.first().t>60_000)h.removeFirst()
        val same=p.zone==fixationZone&&p.x!=null&&p.y!=null&&fixationX!=null&&fixationY!=null&&hypot(p.x!!-fixationX!!,p.y!!-fixationY!!)<.08
        if(!same){fixationStart=now;fixationX=p.x;fixationY=p.y;fixationZone=p.zone}
        val fixation=(now-fixationStart)/1000f;val away=awayStreak(now);val j=jumpRate()
        val event=when{fixation>7.5f&&now-lastEventAt>8000->{lastEventAt=now;"long_fixation"};j>.42f&&fixation<.8f&&now-lastEventAt>5000->{lastEventAt=now;"flighty"};rapidRevisit(now)&&now-lastEventAt>6000->{lastEventAt=now;"rapid_revisit"};else->""}
        return mapOf("study_ratio_15" to ratio(now,15_000),"study_ratio_60" to ratio(now,60_000),"away_streak_seconds" to away,"max_fixation_seconds" to fixation,"jump_rate" to j,"event" to event)
    }
    private fun ratio(now:Long,win:Long):Float{val x=h.filter{now-it.t<=win};if(x.isEmpty())return 0f;val good=x.count{it.p.zone in setOf("laptop","book","tablet")};return good.toFloat()/x.size}
    private fun awayStreak(now:Long):Float{var start=now;for(s in h.reversed()){if(s.p.zone!="away")break;start=s.t};return(now-start)/1000f}
    private fun jumpRate():Float{if(h.size<3)return 0f;var j=0;var n=0;var prev:S?=null;for(s in h){prev?.let{a->n++;val d=if(a.p.x!=null&&s.p.x!=null&&a.p.y!=null&&s.p.y!=null)hypot(a.p.x!!-s.p.x!!,a.p.y!!-s.p.y!!)else if(a.p.zone!=s.p.zone)1f else 0f;if(d>.25f)j++};prev=s};return if(n==0)0f else j.toFloat()/n}
    private fun rapidRevisit(now:Long):Boolean{val cur=h.lastOrNull()?.p?:return false;if(cur.x==null||cur.y==null)return false;return h.any{s->val age=now-s.t;age in 5000..30000&&s.p.x!=null&&s.p.y!=null&&hypot(cur.x!!-s.p.x!!,cur.y!!-s.p.y!!)<.07}}
    private fun hypot(a:Float,b:Float)=sqrt((a*a+b*b).toDouble()).toFloat()
}
