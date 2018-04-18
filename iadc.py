class Iadc(object):
    def __init__(self, fpga, zdok=0):
        self.fpga = fpga
        self.zdok = zdok
        self.reg = 'iadc%d_controller' % self.zdok
        self._set_3wire(0, 0, 1, 0) # initial state

    def reg_reset(self):
        self._set_3wire(0, 0, 1, 0)
        self._set_3wire(1, 0, 1, 0)
        self._set_3wire(0, 0, 1, 0)
        

    def ddrb_reset(self):
        self.fpga.write_int(self.reg, 0, offset=1, blindwrite=True)
        self.fpga.write_int(self.reg, 1, offset=1, blindwrite=True)
        self.fpga.write_int(self.reg, 0, offset=1, blindwrite=True)

    def mmcm_reset(self):
        self.fpga.write_int(self.reg, 0, offset=2, blindwrite=True)
        self.fpga.write_int(self.reg, 1, offset=2, blindwrite=True)
        self.fpga.write_int(self.reg, 0, offset=2, blindwrite=True)

    def _set_3wire(self, mode, clk, ldn, data):
        # bit mappings
        CLK = 0
        DATA = 1
        STROBE = 2
        MODE = 3
        v = (mode << MODE) + (ldn << STROBE) + (data << DATA) + (clk << CLK)
        #print mode, clk, ldn, data,
        #if clk:
        #    print 'Clocked data', data
        #else:
        #    print ''
        self.fpga.write_int(self.reg, v, blindwrite=True)
        
    def write_reg(self, addr, val):
        self._set_3wire(1, 0, 1, 0) # mode high
        self._set_3wire(1, 0, 1, 0) # strobe high
        self._set_3wire(1, 1, 1, 0) # clock tick
        self._set_3wire(1, 0, 1, 0) # 
        self._set_3wire(1, 0, 0, 0) # strobe down
        for i in range(3)[::-1]:
            d = (addr >> i) & 0x1
            self._set_3wire(1, 0, 0, d) # set data bit
            self._set_3wire(1, 1, 0, d) # tick clock
            self._set_3wire(1, 0, 0, d) # 
        for i in range(16)[::-1]:
            d = (val >> i) & 0x1
            self._set_3wire(1, 0, 0, d) # set data bit
            self._set_3wire(1, 1, 0, d) # tick clock
            self._set_3wire(1, 0, 0, d) # 
        # tick clock once more
        self._set_3wire(1, 1, 0, 0) # tick clock
        self._set_3wire(1, 0, 0, 0) # 
        # strobe
        self._set_3wire(1, 0, 1, 0) # tick clock
        self._set_3wire(1, 1, 1, 0) # tick clock
        self._set_3wire(1, 0, 1, 0) # 

    def set_dual_input(self):
        #self.write_reg(0, 0b0111000010111100)
        self.write_reg(0, 0x7cbc)
        self.ddrb_reset()
        self.mmcm_reset()
        self.ddrb_reset()

    def set_single_input(self):
        self.write_reg(0, 0x7cac)
        self.ddrb_reset()
        self.mmcm_reset()
        self.ddrb_reset()

    def set_ramp_mode(self):
        self.write_reg(0b110, 0b11)
        self.ddrb_reset()
        self.mmcm_reset()
        self.ddrb_reset()

    def set_const_mode(self, const=0xaa):
        self.write_reg(0b110, (const<<2) + 0b01)
        self.ddrb_reset()
        self.mmcm_reset()
        self.ddrb_reset()

    def set_data_mode(self):
        self.write_reg(0b110, 0b00)
        self.ddrb_reset()
        self.mmcm_reset()
        self.ddrb_reset()


