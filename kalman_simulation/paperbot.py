import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

class PaperBot:
    def __init__(self, x0, y0, th0):
        self.x = x0
        self.y = y0
        self.th = th0
        self.history = []
        
        self.lidar_f = 0
        self.lidar_r = 0
        self.magnetometer = 0

        self.t = 0
        
        self.dt = 0.1
        self.d = 49
        self.A = 84

        self.dims = [750, 500]
        self.sensors = SensorEstimator(self.dims[0], self.dims[1])
        self._add_history()
        
        self.dconst = self.dt / 2 * np.pi * self.d
        
        # Covariances
        self.R = np.zeros((3, 3))
        self.R[0, 0] = 3.28
        self.R[1, 1] = 1.86
        self.R[2, 2] = 0.8

        # TODO improve this
        self.Q = np.zeros((3, 3))
        self.Q[0, 0] = 0.25 * self.dt
        self.Q[1, 1] = 0.25 * self.dt
        self.Q[2, 2] = 0.89
        
        self.P = self.Q.copy()

        self.jacF = np.eye(3)
        self.jacH = np.eye(3)
    
    
    def _jacobian_H(self, min0=True, min1=True):    # Var to determine if min is l0 or l1
        th0 = self.th
        th1 = self.th + np.pi / 2
        if th1 > 2 * np.pi:
            th1 -= 2 * np.pi
        
        min_arr = [min0, min1]
        
        for i, t in enumerate([th0, th1]):
            truth = min_arr[i]
            dy = self.dims[1] - self.y
            dx = self.dims[0] - self.x
            
            # Gradient with respect to theta (??)
            if t < np.pi / 2:
                if truth:
                    grad = dy * np.tan(t) / np.cos(t)
                else:
                    grad = dx * -1 / (np.sin(t) * np.tan(t))
            elif t < np.pi:
                if truth:
                    grad = dx
            elif t < 3 * np.pi / 2:
                pass
            else:
                pass
        

        # elif Th < self.p2 * 2:
        #     l0 = dx / coth
        #     l1 = Y / sith
        # elif Th < self.p2 * 3:
        #     l0 = Y / coth
        #     l1 = X / sith
        # else:
        #     l0 = X / coth
        #     l1 = dy / sith
        
        
        self.jacH[2, 2] = 1 / (1 + self.th ** 2)


    def _jacobian_F(self, wl, wr):
        self.jacF[0, 0] = 1.
        self.jacF[0, 1] = 0.
        self.jacF[0, 2] = self.dconst * (wl + wr) * -self.ssin(self.th)
        print(self.jacF[0, 2])
        self.jacF[1, 0] = 0.
        self.jacF[1, 1] = 1.
        self.jacF[1, 2] = self.dconst * (wl + wr) * self.scos(self.th)
        
        self.jacF[2, 0] = 0.
        self.jacF[2, 1] = 0.
        self.jacF[2, 2] = 1.
        

    def _add_history(self):
        self.history.append([self.x, self.y, self.th, self.t])
        self.t += 1


    def scos(self, th):
        return np.cos(np.pi / 2 - th)


    def ssin(self, th):
        return np.sin(np.pi / 2 - th)


    def move(self, ul, ur):
        print('t: {} -- X: {}, Y: {}, Th: {}'.format(self.t, self.x, self.y, self.th))
        print('\tul: {}, ur: {}'.format(ul, ur))
        ul -= 90
        ur -= 90
    
        wl = np.sign(ul) * np.power(np.abs(ul), 0.2)
        wr = np.sign(ur) * np.power(np.abs(ur), 0.2)
        print('\tw1: {}, w2: {}'.format(wl, wr))
    
        self.apriori(wl, wr)
        self.sense()
        self._add_history()
        

    def sense(self):
        pass

    def apriori(self, wl, wr):
        dx =  self.dconst * self.scos(self.th) * (wl + wr)
        dy = self.dconst * self.ssin(self.th) * (wl + wr)
        dth = self.dconst / self.A * (wl - wr)

        self.x += dx
        self.y += dy
        self.th += dth

        while self.th > 2 * np.pi:
            self.th -= 2 * np.pi
        while self.th < 0:
            self.th += 2 * np.pi
        
        self._jacobian_F(wl, wr)
        self.P = self.jacF.dot(self.P.dot(self.jacF.T)) + self.Q

            

    def posteriori(self):
        estimates = self.sensors.ret(self.x, self.y, self.th)
        # TODO correctly get this stuff
        
        
        innovation = np.asarray([self.lidar_f - est_F, self.lidar_r - est_R, self.magnetometer - est_M], float)
        innovation_cov = self.jacH.dot(self.P.dot(self.jacH.T)) + self.Q
        
        flag = 1
        while flag:
            try:
                Sinv = np.linalg.inv(innovation_cov)
                flag = 0
            except:
                innovation_cov += np.eye(innovation_cov.shape[0]) * 1e-5
                Sinv = np.eye()
        
        kalman = self.P.dot(self.jacH.T).dot(Sinv)
        
        
    
    def plot_history(self):
        nparr = np.asarray(self.history)
    
        X = list(nparr[:, 0])
        Y = list(nparr[:, 1])
        Th = list(nparr[:, 2])
        t = list(nparr[:, 3])

        fig, ax = plt.subplots(nrows=1, ncols=1)
        
        ax.scatter(X, Y, c=t, cmap='RdBu')
        # plt.colorbar(colormap)
    
        ax.set_title('Position over Time: {} - {}'.format(t[-1], Th[-1]))
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        
        mmin = np.minimum(np.min(X), np.min(Y))
        mmax = np.maximum(np.max(X), np.max(Y))

        # ax.xlim([0, mmax + 250])
        # ax.ylim([0, mmax + 250])
        ax.axis('equal')
        ax.plot([0, self.dims[0], self.dims[0], 0, 0], [0, 0, self.dims[1], self.dims[1], 0], c='k')

        self.sensors.plot_line(X[-1], Y[-1], Th[-1], ax)
        ell = self.plot_ellipse(X[-1], Y[-1])
        ax.add_artist(ell)
        
        plt.show()

    
    def plot_ellipse(self, x, y):
        cov = self.P[:2, :2]
        lambda_, v = np.linalg.eig(cov)
        lambda_ = np.sqrt(lambda_)
        
        ell = Ellipse(xy=(x, y),
                      width=lambda_[0] * 2, height=lambda_[1] * 2,
                      angle=np.rad2deg(np.arccos(v[0, 0])))
        ell.set_facecolor('none')
        return ell
        

class SensorEstimator:
    def __init__(self, xdim, ydim):
        self.x = xdim
        self.y = ydim
        self.p = 2 * np.pi
        self.p2 = np.pi / 2


    def ret(self, X, Y, Th):
        return [self.front_lidar(X, Y, Th), self.right_lidar(X, Y, Th), Th + np.random.normal(0, 0.15)]


    def front_lidar(self, X, Y, Th):
        while Th > self.p:
            Th -= self.p
        while Th < 0:
            Th += self.p

        th0 = Th
        while th0 > self.p2:
            th0 -= self.p2

        coth = np.cos(th0) + 1e-7
        sith = np.sin(th0) + 1e-7
        
        dy = self.y - Y
        dx = self.x - X

        if Th < self.p2 * 1:
            l0 = dy / coth
            l1 = dx / sith
        elif Th < self.p2 * 2:
            l0 = dx / coth
            l1 = Y / sith
        elif Th < self.p2 * 3:
            l0 = Y / coth
            l1 = X / sith
        else:
            l0 = X / coth
            l1 = dy / sith

        return l0, l1


    def right_lidar(self, X, Y, Th):
        return self.front_lidar(X, Y, Th + self.p2)


    def plot_line(self, X, Y, Th, ax):
        lf0, lf1 = self.front_lidar(X, Y, Th)
        lf = min(lf0, lf1)
        lr0, lr1 = self.right_lidar(X, Y, Th)
        lr = min(lr0, lr1)

        p21X = X + np.cos(self.p2 - Th) * lf
        p21Y = Y + np.sin(self.p2 - Th) * lf

        p22X = X + np.cos(-Th) * lr
        p22Y = Y + np.sin(-Th) * lr

        ax.plot([X, p21X], [Y, p21Y],c='r', label='Front')
        ax.plot([X, p22X], [Y, p22Y],c='b', label='Right')
        ax.legend()
