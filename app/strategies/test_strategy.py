class TestStrategy:
    def on_start(self,config):
        self.bar_count=0
    def on_bar(self,candle):
        self.bar_count+=1
        if self.bar_count==2:
            return type("Signal",(),{'action':'BUY'})()
        elif self.bar_count == 4:
            return type('Signal', (), {'action': 'SELL'})()
        else:
            return type('Signal', (), {'action': 'HOLD'})()