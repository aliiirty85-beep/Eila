package com.eila.ballrival
object OverlayBus {
    @Volatile var config=OverlayConfig()
    @Volatile var service:OverlayService?=null
}
