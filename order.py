class Order:
    type_buy  = 0
    type_sell = 1

    def __init__(self, bot, price, order_type):
        self.type = order_type
        self.age = 0
        
        self.price = price
        self.avg_price = price
        self.curr_price = 0
        self.last_price = 0
        
        self.bot = bot
        self.stop_loss = bot.stop_loss
        self.take_profit = bot.take_profit
        self.tp_decrement = .040/100*self.take_profit
        self.sl_decrement = .015/100*self.stop_loss

        self.loss_duration = 0
        self.max_loss_duration = bot.max_loss_duration

        self.db_id  = None
        self.ticket = None
    
    def update(self, curr_price, update_avg=True):
        self.curr_price = curr_price
        self.age += 1

        if update_avg:
            self.avg_price = (.9*self.age*self.avg_price+curr_price)/(.9*self.age+1)
            self.last_price = curr_price

        if self.age > 60 \
        and (self.avg_price-curr_price)/self.avg_price < 0.005:
            self.take_profit = max(-1*self.bot.stop_loss, self.take_profit-self.tp_decrement)
            self.stop_loss = min(0, self.stop_loss-self.sl_decrement)
        elif self.get_gain() < 0:
            self.stop_loss = min(0, self.stop_loss-self.sl_decrement)

        if self.get_gain() <= self.stop_loss:
            self.loss_duration += 2.5*(self.get_gain()/self.stop_loss)
        else:
            self.loss_duration = 0
    
    def get_gain(self, adj=True):
        gain = 0
        if adj:
            if self.type == Order.type_buy:
                self.price = min(self.price, self.get_mt5_tp())
                self.price = max(self.price, self.get_mt5_sl())
            else:
                self.price = max(self.price, self.get_mt5_tp())
                self.price = min(self.price, self.get_mt5_sl())
            
        if self.type == Order.type_buy:
            gain = (self.curr_price-self.price)/self.price
            if gain > 1: gain -= 1
        else:
            gain = self.price/self.curr_price - 1
        return gain
    
    def get_real_sl(self):
        if self.type == Order.type_buy:
            return self.price * (1+self.stop_loss)
        else:
            return self.price / (1-self.stop_loss)

    def get_real_tp(self):
        if self.type == Order.type_buy:
            return self.price * (1+self.take_profit)
        else:
            return self.price / (1-self.take_profit)

    def get_mt5_sl(self):
        if self.type == Order.type_buy:
            return self.price * (1+1.3*self.bot.stop_loss)
        else:
            return self.price / (1+1.3*self.bot.stop_loss)

    def get_mt5_tp(self):
        if self.type == Order.type_buy:
            return self.price * (1+self.bot.take_profit)
        else:
            return self.price / (1+self.bot.take_profit)

    def is_stop(self):
        if self.get_gain(False) < 1.5*self.bot.stop_loss:
            return True
        if self.get_gain() <= self.stop_loss \
        and self.loss_duration > self.max_loss_duration:
            return True
        return False
    
    def is_take(self):
        if self.get_gain(False) > self.bot.take_profit:
            return True
        return self.get_gain() >= self.take_profit

    def __repr__(self):
        return "< %s  G: %+.4f  SL: %.4f  TP: %.4f  %4d >"%(
            'BUY ' if self.type == Order.type_buy else 'SELL',
            self.get_gain(), 
            self.stop_loss,
            self.take_profit,
            self.loss_duration,
        )
