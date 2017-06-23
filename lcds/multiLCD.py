import RPi_I2C_driver


class MultipleLCDs:
    lcds = {}

    def __init__(self, addresses):
        for i in addresses:
            print("Initializing LCD on", i)
            self.lcds[i] = RPi_I2C_driver.lcd(i)
        print(self.lcds)

    def lcd_display_string(self, s, i):
        for i in self.lcds:
            self.lcds[i].lcd_display_string(s, i)

    def lcd_clear(self):
        for i in self.lcds:
            self.lcds[i].lcd_clear()

    def lcd_load_custom_chars(self, fontdata):
        for i in self.lcds:
            self.lcds[i].lcd_load_custom_chars(fontdata)

    def backlight(self, backlight):
        for i in self.lcds:
            self.lcds[i].backlight(backlight)

    def lcd_write(self, w):
        for i in self.lcds:
            self.lcds[i].lcd_write(w)

    def lcd_write_char(self, c):
        for i in self.lcds:
            self.lcds[i].lcd_write_char(c)

    def lcd_display_string_pos(self, s, x, y):
        for i in self.lcds:
            self.lcds[i].lcd_display_string_pos(s, x, y)
