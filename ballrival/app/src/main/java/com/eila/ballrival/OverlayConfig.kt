package com.eila.ballrival

data class OverlayConfig(
    var minBalls:Int=3,
    var maxBalls:Int=7,
    var minSizeDp:Int=70,
    var maxSizeDp:Int=150,
    var minStayMs:Long=1000,
    var maxStayMs:Long=8000,
    var minOpacity:Int=45,
    var maxOpacity:Int=100,
    var tapDestroys:Boolean=true,
    var tabletBoost:Boolean=true,
    var eilaEnabled:Boolean=false,
    var eilaUrl:String="",
    var eilaToken:String=""
)
