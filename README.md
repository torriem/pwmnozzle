pwmnozzle.py
------------
This python script demonstrates how pulse width modulation of a
sprayer nozzle could be controlled.  It shows how to generate
the information needed by the PID loops to make it work.

The script implements a simple nozzle abstraction, and then a
sprayer abstraction to make it easier to set things like nozzle
type, spacing, number of nozzles, pressure, desired rates and
speeds, etc. the output of the script draws graphs similar to the
graph of Aim Command Pro, showing the duty cycles across the
boom.  One interesting thing this graph showed me is that when
turning such that part of the boom is going backwards, the total
flow rate in the manifold actually increases slightly over when
it's not. This was counter-intuitive to me at first.

Theory of operation
-------------------
PWM nozzle control is based on the idea of keeping the liquid 
manifold at a constant pressure, regardless of flow rate, limited
by the nozzle size.  To achieve this, the nozzles are pulsed on
and off rapidly with solenoids.  Usually odd and even nozzles are
pulsed oppositely (180 degrees out of phase), to even out the
spray pattern.

Control is as follows.  A PID loop keeps the pressure constant by
either opening and closing a valve feeding the manifold, or more
ideally controlling hydraulic flow to a hydraulically-driven water
pump.  A computer then figures out based on the desired application
rate, the ground speed, and the yaw rate, what manifold flow rate
is needed to provide this rate, compensating for yaw motion across
the boom.  Finally a PID controller tries to maintain the desired
flow rate by adjusting the baseline PWM duty cycle up or down.  

The computer calculates the duty cycle for each individual nozzle 
based on the baseline duty cycle, given the calculated speed resulting
from the yaw rate, which is sent to each nozzle solenoid through a
PWM motor driver, synchronized as described previously.

Since it's possible for a nozzle to travel faster than the maximum
speed given a nozzle size and pressure, the computer calculates a
theoretical limit to a nozzle's flow and uses that to cap the rate.
After all a duty cycle cannot exceed 100%.  This cap allows the
overall flow rate to be more accurately calculated. Without the cap,
the flow rate PID loop might over-apply across the boom, thinking it
needs to produce flow rates in excess of what the fastest-moving
nozzles can apply.

These cap calculations require information about the nozzle size
(it's calibrated rate) and specific gravity of the fluid being
applied.  This is likely why Aim Command Pro requires nozzle size
to be set to get accurate results.

Rather than simply drive the baseline PWM duty cycle from the PID
loop, an alternative may be to use the theoretical calculations to
set the baseline duty cycle, and then have PID simply adjust it up
or down slightly to achieve the actual desired flow rate. Reality is
always a bit different than the calculations.

Also, the computer doing the calculations could communicate with the 
pressure PID loop to make a note of the parameters given various 
states of the nozzles.  Then when going from all nozzles off to turning
them back on again, it could prime the pressure PID loop with better
starting values so it will settle in faster.

