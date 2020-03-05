import math

#SQUARE_DIST_TO_AREA = 10000 #10000 m^2 per hectare
SQUARE_DIST_TO_AREA = 43560 #ft^2 per acre
DIST_CONV = 5280 #ft per mile
SPEED_CONV = 5280 / 3600 #mph to ft/second
#BASE_PRESSURE = 2.76 #bar (40psi) baseline water pressure
BASE_PRESSURE = 40 #40psi baseline water pressure
#base_nozzle = 2.27 #l/min (0.6 gpm)

class Nozzle(object):
    def __repr__(self):
        return "nozzle at %.2f with %.2f width" % (self.position, self.width)


    def __init__ (self, width, position):
        self.width = width
        self.position = position
        self.on = True

    def change_ratio(self, speed, yaw_rate):
        # yaw rate is degrees per second
        # positive yaw is to right (clockwise)
        # negative position is to left
        speed = speed * SPEED_CONV
        speed_difference = yaw_rate / 360 * -self.position
        adjustment = (speed_difference + speed) / speed

        # returns a change ratio that can be applied to PWM rate, speed, or volume
        return adjustment

    def pwm_adjust_and_rate(self, desired_rate, desired_speed, desired_pressure, yaw_rate):
        # Return PWM adjustment factor, and also compensated rate

        # yaw rate is degrees per second
        # positive yaw is to right (clockwise)
        # negative position is to left
        if not self.on:
            return (0,0) #no pwm, no actual volume

        adjustment = self.change_ratio(desired_speed, yaw_rate)

        rate = desired_rate / SQUARE_DIST_TO_AREA * desired_speed * self.width * 60.0
        rate *= adjustment # compensated volume/minute required

        # cap the calculated rate at 100% duty cycle
        if rate > self.nozzle_rate_at_press(desired_pressure):
            # volume required exceed theoretical maximum; cap it
            rate = self.nozzle_rate_at_press(desired_pressure)

        return (adjustment, rate)

class Sprayer(object):
    def __init__(self, num_nozzles, nozzle_spacing, nozzle_size, specific_gravity):
        self.num_nozzles = num_nozzles
        self.spacing = nozzle_spacing
        self.size = nozzle_size
        self.gravity = specific_gravity

        self.nozzles = []
        width = self.num_nozzles * self.spacing

        # set up nozzles, automatically calculating position, where
        # zero is the center
        for x in range(self.num_nozzles):
            position = (x+1 - self.num_nozzles / 2) * self.spacing - self.spacing / 2
            nozzle = Nozzle(self.spacing, position)

            self.nozzles.append(nozzle)

    def nozzle_rate_at_press(self, pressure):
        # Calculate the volume per minute at pressure,
        # compensated for specific gravity
        return self.size * math.sqrt(pressure / BASE_PRESSURE) / \
                           math.sqrt(self.gravity)

    def get_nozzle_rate(self, vol_area_rate, desired_speed):
        # one nozzle flow rate at this vol per area rate
        return  vol_area_rate / SQUARE_DIST_TO_AREA * desired_speed * \
                      SPEED_CONV * self.spacing * 60


    def baseline_pwm(self, vol_area_rate, desired_speed, pressure):
        # calculate PWM needed to achieve desired rate at
        # desired speed, pressure, and rate (volume per area)

        # what fraction of the normal rate at pressure to get our desired
        # rate?
        pwm = (self.get_nozzle_rate(vol_area_rate, desired_speed) / \
              self.nozzle_rate_at_press(pressure))

        if pwm > 1: return 1 #exceeded capability of nozzle. Underspray situation!
        return pwm

    def get_compensated_values(self, desired_rate, desired_speed, desired_pressure, yaw_rate):
        ratios = []

        # determine volume distribution across boom, capping any values
        # that will exceed 100% duty cycle.
        total_rate = 0

        for nozzle in self.nozzles:
            ratio = nozzle.change_ratio(desired_speed, yaw_rate)
            rate = self.get_nozzle_rate(desired_rate, desired_speed) * ratio
            if rate > self.nozzle_rate_at_press(desired_pressure):
                # if duty cycle will likely exceed 100%, cap it
                rate = self.nozzle_rate_at_press(desired_pressure)
            elif rate < 0:
                # nozzle going backwards, shut off
                rate = 0
                ratio = 0
       
            #print (nozzle.position * 12, ratio, rate)

            if nozzle.on:
                ratios.append(ratio)
                total_rate += rate
            else:
                ratios.append(0)
        return total_rate, ratios

    def nozzles_on(self, nozzle_nums, is_on):
        for n in nozzle_nums:
            self.nozzles[n].on = is_on

def print_graph(pwm, ratios):
    nozzlegraphs = []
    last = 1
    for n in ratios:
        dutycycle = n * pwm * 10
        if dutycycle < 0.5:
            dutycycle = 0
        elif dutycycle > 10:
            dutycycle = 10
        else:
            dutycycle = round(dutycycle)

        if dutycycle > 0:
            graph = 'A' + '#' * (dutycycle - 1) + "#" + '.' * (10 - dutycycle)
        else:
            graph = 'X..........'
            last = 0
    
        nozzlegraphs.append(graph)

    for r in range(10,-1,-1):
        for n in nozzlegraphs:
            print (n[r], end="")

        print ()

    print("=" * len(ratios))



if __name__ == "__main__":
    # 72 nozzles, 20 inches apart, 06 (0.6gpm)
    print ("120' boom, 72 nozzles, 20 inch spacing, 06 nozzles, water")
    s = Sprayer(72, 20.0/12.0, 0.6, 1)
    press = 50 #psi
    speed = 8 #mph
    spray_rate = 10 #gpa

    #print (s.nozzles)
    # this calculation is affected by specific gravity
    print ("nozzle gpm at %d psi: %0.2f" % (press, s.nozzle_rate_at_press(press)))

    # this calculation is affected by specific gravity
    pwm = s.baseline_pwm(10, speed, 50)
    print ("theoretical baseline duty cycle for %d mph: %0.2f" % (speed,pwm))
    
    def do_yaw(speed, yaw_rate):
        print ("At %d mph, at %d deg/second, with a rate of %d gal/acre, " % (speed, yaw_rate, spray_rate), end="")
        rate,ratios = s.get_compensated_values(10,speed,50,yaw_rate)
        print ("%0.2f gpm flow required." % rate)
        if (max(ratios) * pwm) > 1:
            print("Warning! at %d deg/second, some nozzles are at 100%% duty cycle and under applying." % yaw_rate )
        print_graph(pwm, ratios)
       
    do_yaw(8,0)
    do_yaw(8,40)
    do_yaw(8,80)
    do_yaw(8,120)
    do_yaw(8,160)
    do_yaw(8,200)
    do_yaw(8,240)
    s.nozzles_on(range(0,10), False)
    s.nozzles_on(range(40,50), False)
    do_yaw(8,120)
    do_yaw(10,120)
    do_yaw(8,-160)



