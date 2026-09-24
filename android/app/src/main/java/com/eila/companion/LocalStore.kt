package com.eila.companion

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

data class LocalReturn(val id:Long,val dueAt:Long,val text:String,val lastStage:Int)

class LocalStore(context:Context):SQLiteOpenHelper(context,"eila_local.db",null,1){
    override fun onCreate(db:SQLiteDatabase){
        db.execSQL("create table if not exists return_contracts(id integer primary key,due_at integer not null,text text not null,last_stage integer default -1,status text default 'pending')")
        db.execSQL("create table if not exists kv(k text primary key,v text not null)")
    }
    override fun onUpgrade(db:SQLiteDatabase,oldVersion:Int,newVersion:Int)=Unit
    fun saveReturn(id:Long,dueAt:Long,text:String){
        val v=ContentValues().apply{put("id",id);put("due_at",dueAt);put("text",text);put("last_stage",-1);put("status","pending")}
        writableDatabase.insertWithOnConflict("return_contracts",null,v,SQLiteDatabase.CONFLICT_REPLACE)
    }
    fun pendingReturns():List<LocalReturn>{
        val out=mutableListOf<LocalReturn>();val c=readableDatabase.rawQuery("select id,due_at,text,last_stage from return_contracts where status='pending'",null)
        c.use{while(it.moveToNext())out+=LocalReturn(it.getLong(0),it.getLong(1),it.getString(2),it.getInt(3))}
        return out
    }
    fun setReturnStage(id:Long,stage:Int){writableDatabase.execSQL("update return_contracts set last_stage=? where id=?",arrayOf(stage,id))}
    fun finishReturn(id:Long){writableDatabase.execSQL("update return_contracts set status='done' where id=?",arrayOf(id))}
    fun put(k:String,v:String){val x=ContentValues().apply{put("k",k);put("v",v)};writableDatabase.insertWithOnConflict("kv",null,x,SQLiteDatabase.CONFLICT_REPLACE)}
    fun get(k:String):String?{val c=readableDatabase.rawQuery("select v from kv where k=?",arrayOf(k));c.use{return if(it.moveToFirst())it.getString(0) else null}}
}
