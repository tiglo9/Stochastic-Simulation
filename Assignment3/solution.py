from numpy.random import uniform, exponential
from numpy import sin, pi, std, sqrt
from statistics import SampleStatistic
from core import Simulation, Event
import scipy

v_1 = False

class SimInfo:
    def __init__(self, sim, stats):
        self.sim = sim
        self.inPatientTravelling = False
        self.inPatientInWaitingRoom = False
        self.inPatientQueue = []
        self.outPatientWaitingList = []
        self.EmWaitingRoom = []
        self.InOutWaitingRoom = []
        self.busyScanners = 0
        self.reset_out_schedule()
        self.stats = stats

    def reset_out_schedule(self):
        self.OutSchedule = {0: {}, 1: {}, 2: {}, 3: {}, 4: {}}
        i = 8
        while i < 12:
            for j in range(5):
                self.OutSchedule[j][i] = None
            i += 0.25
        while i < 16:
            for j in range(5):
                if i % 1 == 0.75:
                    self.OutSchedule[j][i] = "Restricted"
                else:
                    self.OutSchedule[j][i] = None
            i += 0.25

    def schedule_waiting_list(self):
        i = 8
        while i < 12:
            for j in range(5):
                if self.outPatientWaitingList:
                    self.OutSchedule[j][i] = self.outPatientWaitingList.pop(0)
                else:
                    return
            i += 0.25
        while i < 16:
            for j in range(5):
                if i % 1 == 0.75:
                    self.OutSchedule[j][i] = "Restricted"
                elif self.outPatientWaitingList:
                    self.OutSchedule[j][i] = self.outPatientWaitingList.pop(0)
                else:
                    return
            i += 0.25

    def add_to_waiting_room(self, patient):
        self.stats.enter_waiting_room(len(self.EmWaitingRoom + self.InOutWaitingRoom) >= 3)
        # if self.stats.batch.total_patients > 200:
        #     self.stats.new_batch()
        global v_1
        if (IsWorkingHours(self.sim.current_time) and ((not v_1 and self.busyScanners < 2 )or self.busyScanners == 0)) or self.busyScanners == 0:

            self.start_scan(patient)
        elif patient.type == "em":
            self.EmWaitingRoom.append(patient)
        else:
            self.InOutWaitingRoom.append(patient)

    def start_scan(self, patient):
        # print(f"starting scan at {self.sim.current_time % 24} for {patient.type}")
        # print(self.EmWaitingRoom + self.InOutWaitingRoom)

        self.stats.waiting_time(patient, self.sim.current_time)
        if patient.type == "in":
            self.stats.inpatient(patient, self.sim.current_time)

            self.inPatientInWaitingRoom = False
            if self.inPatientQueue:
                p = self.inPatientQueue.pop(0)
                self.inPatientTravelling = True
                arrival = InpatientArrival(self.sim.current_time + WalkingDuration(), self, p)
                self.sim.schedule(arrival)
        duration = ScanDuration()
        self.sim.schedule(EndScan(self.sim.current_time + duration, self, patient))

        if (duration + self.sim.current_time) %24 > 16:
            self.stats.ct_used(16-((self.sim.current_time) %24), IsWorkingHours(self.sim.current_time))
            self.stats.ct_used((duration - (16-(self.sim.current_time) %24)), False)
        else:
            self.stats.ct_used(duration, IsWorkingHours(self.sim.current_time))
        self.busyScanners += 1
        # print(f"{self.busyScanners} busy scanners\n")

    def end_scan(self, patient):
        self.busyScanners -= 1
        if ((not v_1) and (IsWorkingHours(self.sim.current_time) or self.busyScanners == 0)) or self.busyScanners == 0:
            if len(self.EmWaitingRoom) != 0:
                self.start_scan(self.EmWaitingRoom.pop(0))
            elif len(self.InOutWaitingRoom) != 0:
                self.start_scan(self.InOutWaitingRoom.pop(0))

    def schedule_outpatient(self):
        patient = Patient("out", 0, call_time=self.sim.current_time)
        time = NextWorkDay(self.sim.current_time)
        day = (time % (7 * 24)) // 24
        while day < 5:
            i = 8
            while i < 12:
                if self.OutSchedule[day][i] is None:
                    self.OutSchedule[day][i] = patient
                    return
                i += 0.25
            while i < 16:
                if i % 1 == 0.75:
                    self.OutSchedule[day][i] = "Restricted"
                elif self.OutSchedule[day][i] is None:
                    self.OutSchedule[day][i] = patient
                    return
                i += 0.25
            day += 1
        # print((time % (7 * 24)) // 24)
        self.outPatientWaitingList.append(patient)


class InpatientArrival(Event):
    def __init__(self, time: float, info, patient):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.info = info
        self.patient = patient
        patient.arrival_time = time

    def execute(self, sim: "Simulation") -> None:
        # print("inpatient arrived")
        self.info.inPatientTravelling = False
        self.info.inPatientInWaitingRoom = True
        self.info.add_to_waiting_room(self.patient)


class InpatientRequest(Event):
    def __init__(self, time: float, info):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.info = info

    def execute(self, sim: "Simulation") -> None:
        patient = Patient("in", 0, call_time=self.time)
        # print("inp")
        if self.info.inPatientInWaitingRoom or self.info.inPatientTravelling:
            self.info.inPatientQueue.append(patient)
        else:
            arrival = InpatientArrival(sim.current_time + WalkingDuration(), self.info, patient)
            sim.schedule(arrival)
            self.info.inPatientTravelling = True
        self.schedule_next(sim)

    def schedule_next(self, sim):
        next_time = self.time
        while 59:
            lambda_max = 6 / 16 + 6
            next_time += exponential(1 / lambda_max)
            if uniform(0, 1) < InpatientArrivalRate(next_time) / lambda_max:
                break
        sim.schedule(InpatientRequest(next_time, self.info))


class OutpatientCall(Event):
    def __init__(self, time: float, info):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.info = info

    def execute(self, sim: "Simulation") -> None:
        self.info.schedule_outpatient()
        self.schedule_next(sim)

    def schedule_next(self, sim):
        scale = 8 / 23
        next_time = sim.current_time + exponential(scale)
        while not IsWorkingHours(next_time):
            next_time = NextWorkDay(next_time) + exponential(scale)
        sim.schedule(OutpatientCall(next_time, self.info))


class EmPatientArrival(Event):
    def __init__(self, time: float, info):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.info = info

    def execute(self, sim: "Simulation") -> None:
        self.info.add_to_waiting_room(Patient("em", sim.current_time))

        self.schedule_next(sim)

    def schedule_next(self, sim):
        scale = 1
        next_time = sim.current_time + exponential(scale)
        sim.schedule(EmPatientArrival(next_time, self.info))


class EndScan(Event):
    def __init__(self, time: float, info, patient):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.info = info
        self.patient = patient

    def execute(self, sim: "Simulation") -> None:
        self.info.end_scan(self.patient)


class CheckSchedule(Event):
    def __init__(self, time: float, info):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.info = info

    def execute(self, sim: "Simulation") -> None:
        time = self.time
        day = (time % (24 * 7)) // 24
        hour = time % 24
        # print(time)
        if self.info.OutSchedule[day][hour] != "Restricted" and self.info.OutSchedule[day][hour] is not None:
            if uniform(0, 1) < 0.84:
                self.info.OutSchedule[day][hour].arrival_time = self.info.sim.current_time
                self.info.add_to_waiting_room(self.info.OutSchedule[day][hour])
            self.info.stats.access_time(self.time - self.info.OutSchedule[day][hour].call_time)
        self.schedule_next(sim)

    def schedule_next(self, sim):
        next_time = self.time + 0.25
        if not IsWorkingHours(next_time):
            next_time = NextWorkDay(next_time)

        sim.schedule(CheckSchedule(next_time, self.info))


class ScheduleOut(Event):
    def __init__(self, time: float, info):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.info = info

    def execute(self, sim: "Simulation") -> None:
        self.info.reset_out_schedule()
        self.info.schedule_waiting_list()
        self.schedule_next(sim)

    def schedule_next(self, sim):
        next_time = self.time - (self.time % (7 * 24)) + 11 * 24 + 16

        sim.schedule(ScheduleOut(next_time, self.info))


class RefreshBatch(Event):
    def __init__(self, time: float, info):
        self.time: float = time
        self.cancelled: bool = False
        self._seq: int = 0  # set by Simulation.schedule()
        self.info = info

    def execute(self, sim: "Simulation") -> None:
        self.info.stats.new_batch()
        sim.schedule(RefreshBatch(self.time + 4 * 7*24*4, self.info))


class Patient:
    def __init__(self, patient_type, arrival_time, call_time=0):
        self.arrival_time = arrival_time
        self.type = patient_type
        self.call_time = call_time

    def __repr__(self):
        return self.type


def IsWorkingHours(time):
    day = (time % (24 * 7)) // 24
    hour = time % 24
    return day <= 4 and 8 <= hour < 16


def NextWorkDay(time):
    if time % (24 * 7) >= (4 * 24):
        return time - (time % (24 * 7)) + 24 * 7 + 8
    return time - (time % 24) + 24 + 8


def ScanDuration():
    global v_1
    if v_1:
        return exponential(14.5) / 60
    return uniform(10, 19) / 60  # time in hours


def WalkingDuration():
    return uniform(9, 15) / 60  # time in hours


def InpatientArrivalRate(time):
    hour = time % 24
    # lambda_I = 6/16
    result = 6 / 16
    if hour >= 9 and hour <= 15 and IsWorkingHours(time):
        result += 6 * sin(pi / 3 * (hour - 9)) ** 2
    return result


class Batch:
    def __init__(self):
        self.access_time = SampleStatistic()
        self.waiting_time_em = SampleStatistic()
        self.waiting_time_out = SampleStatistic()
        self.patients_outside = 0
        self.total_patients = 0
        self.inpatients_not_scanned_before_16 = 0
        self.total_inpatients = 0
        self.ct_util_office = 0
        self.ct_util_no_office = 0


class Stats:
    def __init__(self, sim):
        self.batch = Batch()
        self.batch_archive = []
        self.sim = sim

    def ct_used(self, time, is_working_hours):
        if is_working_hours:
            self.batch.ct_util_office += time
        else:
            self.batch.ct_util_no_office += time
    def new_batch(self):
        print(f"Batch {len(self.batch_archive)}")
        self.batch_archive.append(self.batch)
        self.batch = Batch()
        if len(self.batch_archive) > 100:
            self.sim.stop()

    def enter_waiting_room(self, bool):
        if bool:
            self.batch.patients_outside += 1
        self.batch.total_patients += 1

    def access_time(self, time):
        self.batch.access_time.record(time / 24)

    def waiting_time(self, patient, time):
        if patient.type == "em":
            self.batch.waiting_time_em.record(time - patient.arrival_time)
        elif patient.type == "out":
            self.batch.waiting_time_out.record(time - patient.arrival_time)

    def inpatient(self, patient, time):
        if not IsWorkingHours(patient.call_time):
            return
        if not (time - patient.call_time < 10 and time % 24 < 16 and time % 24 > 8):
            self.batch.inpatients_not_scanned_before_16 += 1
        self.batch.total_inpatients += 1

    def print_stats(self):
        self.batch_archive.pop(0) #first batch is warm up
        office_hours = 5*8*4*4 * 2
        no_office_hours = 5*16*4*4 + 2 * 24*4*4
        util = [batch.ct_util_office/office_hours for batch in self.batch_archive]
        print(
            f"the CT utilization during office hours is {sum(util) / len(util)} with 95% CI ({sum(util) / len(util) - 1.96 * std(util, ddof=1) / sqrt(len(util))},{sum(util) / len(util) + 1.96 * std(util, ddof=1) / sqrt(len(util))})")
        (calculate_r(util))
        util = [batch.ct_util_no_office / no_office_hours for batch in self.batch_archive]
        print(
            f"the CT utilization outside office hours is {sum(util) / len(util)} with 95% CI ({sum(util) / len(util) - 1.96 * std(util, ddof=1) / sqrt(len(util))},{sum(util) / len(util) + 1.96 * std(util, ddof=1) / sqrt(len(util))})")
        (calculate_r(util))
        access = [batch.access_time.mean() for batch in self.batch_archive]
        print(
            f"the average access time for outpatients is {sum(access) / len(access)} days with 95% CI ({sum(access) / len(access) - 1.96 * std(access, ddof=1) / sqrt(len(access))},{sum(access) / len(access) + 1.96 * std(access, ddof=1) / sqrt(len(access))})")
        (calculate_r(access))
        em = [batch.waiting_time_em.mean() * 60 for batch in self.batch_archive]
        print(
            f"the average waiting time for emergency patients is {sum(em) / len(em)} minutes with 95% CI ({sum(em) / len(em) - 1.96 * std(em, ddof=1) / sqrt(len(em))},{sum(em) / len(em) + 1.96 * std(em, ddof=1) / sqrt(len(em))})")
        (calculate_r(em))
        out = [batch.waiting_time_out.mean() * 60 for batch in self.batch_archive]
        print(
            f"the average waiting time for outpatients is {sum(out) / len(out)} minutes with 95% CI ({sum(out) / len(out) - 1.96 * std(out, ddof=1) / sqrt(len(out))},{sum(out) / len(out) + 1.96 * std(out, ddof=1) / sqrt(len(out))})")
        (calculate_r(out))
        outside = [batch.patients_outside / batch.total_patients for batch in self.batch_archive]
        print(
            f"the fraction of CT patients that have to wait outside of the waiting room is {sum(outside) / len(outside)} with 95% CI ({sum(outside) / len(outside) - 1.96 * std(outside, ddof=1) / sqrt(len(outside))},{sum(outside) / len(outside) + 1.96 * std(outside, ddof=1) / sqrt(len(outside))})")
        (calculate_r(outside))
        global v_1
        if not v_1:
            after16 = [batch.inpatients_not_scanned_before_16 / batch.total_inpatients for batch in self.batch_archive]
            print(
                f"the fraction of inpatients that were not scanned the same workday is {sum(after16) / len(after16)} with 95% CI ({sum(after16) / len(after16) - 1.96 * std(after16, ddof=1) / sqrt(len(after16))},{sum(after16) / len(after16) + 1.96 * std(after16, ddof=1) / sqrt(len(after16))})")
            (calculate_r(after16))

def startSimulation():
    sim = Simulation()
    stats = Stats(sim)
    info = SimInfo(sim, stats)
    EmPatientArrival(0, info).schedule_next(sim)
    global v_1
    if not v_1:
        InpatientRequest(0, info).schedule_next(sim)
        OutpatientCall(0, info).schedule_next(sim)
        CheckSchedule(-1, info).schedule_next(sim)
        ScheduleOut(-1, info).schedule_next(sim)
    sim.schedule(RefreshBatch(7*24*4, info))
    sim.run()
    stats.print_stats()
    return


def calculate_r(l):
    r = len(l)
    delta = 0.1
    t = scipy.stats.t.ppf(1 - 0.05 / 2, r - 1)
    print('is it true?')
    print(r >= t ** 2 * std(l, ddof=1) ** 2 / (delta / (1 + delta) * sum(l) / r) ** 2)

if __name__ == "__main__":
    sim = startSimulation()
