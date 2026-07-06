# q1 模型推导

## 1. 基本变量与单位

令时间为 `t (s)`，水平地面距离为 `x(t) (m)`，高度为 `h(t) (m)`，真空速为 `V(t) (m/s)`，飞机质量为 `m(t) (kg)`。小航迹角巡航爬升下，题面所称高度和空速控制变量解释为轨迹决策变量；实际物理控制量为推力 `T(t)` 与航迹角 `gamma(t)`。

## 2. 大气密度、温度和声速

第一问密度采用题设指数模型

```text
rho(h)=rho0 exp(-h/Hrho),
```

其中 `rho0=1.225 kg/m^3`，`Hrho=7300 m`。等马赫策略需要声速模型，采用标准对流层近似

```text
Tatm(h)=T0-Lh,
a(h)=sqrt(gamma_air R_air Tatm(h)).
```

该模型只在温度为正的高度范围内使用。

## 3. 升力平衡与阻力极曲线

小航迹角准稳态巡航爬升满足

```text
L = 0.5 rho(h) V^2 S CL ≈ mg.
```

因此

```text
CL = 2mg / [rho(h) V^2 S].
```

阻力极曲线采用

```text
CD = CD0 + k CL^2,
D = 0.5 rho(h) V^2 S CD.
```

代入升力平衡后，阻力也可写成寄生阻力与诱导阻力之和。

## 4. 水平位移和风场

用户确认 q1 主风场为

```text
W(h)=20+3e-5(h-10000)^2.
```

取正值表示顺航向风，小角度下

```text
dx/dt = V cos(gamma) + W(h) ≈ V + W(h).
```

## 5. 能量方程、推力和质量变化

纵向动力学为

```text
m dV/dt = T - D - mg sin(gamma).
```

利用 `sin(gamma)=dh/dt / V` 得

```text
T = D + m dV/dt + (mg/V) dh/dt.
```

燃油消耗率采用题面二次速度惩罚形式

```text
dm/dt = -cT T [1 + beta (V - Vopt)^2].
```

其中 `beta` 单位为 `s^2/m^2`，使括号内为无量纲。

## 6. q1 闭合条件

题面只给出等速或等马赫策略，不足以唯一确定高度演化。为闭合巡航爬升模型，采用操作假设：飞机通过连续调整迎角，使升力系数保持参考值

```text
CL = CL_ref = 2 m0 g / [rho(h0) V0^2 S].
```

按题设初始状态计算 `CL_ref=0.658914`。抛物线阻力极曲的最大升阻比升力系数为

```text
CL_(L/D max) = sqrt(CD0/k) = 0.699206.
```

二者接近，说明该参考值对应接近高升阻比的巡航状态；但它仍是为使两种策略可计算而加入的闭合假设，不是题面或升力平衡唯一决定的结果。这样质量下降时，飞机通过改变高度/速度维持升力平衡。

## 7. 策略 A：等真空速巡航爬升

令

```text
V(t)=V0.
```

由 `CL=CL_ref` 和升力平衡，

```text
m(t)/m0 = rho(h(t))/rho(h0).
```

采用指数密度模型得到

```text
h(t)=h0-Hrho ln[m(t)/m0],
dh/dm = -Hrho/m.
```

且 `dV/dm=0`。将 `dh/dt=(dh/dm)(dm/dt)` 代入能量方程，可得质量的一维隐式微分方程。

## 8. 策略 B：等马赫数巡航爬升

令

```text
M(t)=M0=V0/a(h0),
V(t)=M0 a(h(t)).
```

由 `CL=CL_ref` 得

```text
m(t)/m0 = rho(h(t)) a(h(t))^2 / [rho(h0) a(h0)^2].
```

微分形式为

```text
(1/m) dm/dt = [d ln rho/dh + 2 d ln a/dh] dh/dt,
dh/dm = 1 / {m [d ln rho/dh + 2 d ln a/dh]}.
```

又有

```text
dV/dm = V (d ln a/dh) dh/dm.
```

## 9. 隐式质量方程

两种策略都可写成 `h=h(m)`、`V=V(m)`。定义

```text
A(m)=m dV/dm + (mg/V) dh/dm,
Phi(V)=1+beta(V-Vopt)^2.
```

则

```text
T = D + A(m) dm/dt,
dm/dt = -cT Phi(V) [D + A(m) dm/dt].
```

解得

```text
dm/dt = - cT Phi(V) D / [1 + cT Phi(V) A(m)].
```

这是一维常微分方程，数值积分至 `m(tf)=62000 kg`。

## 10. 可行域和验证

可行域要求：密度、温度、声速、阻力、推力和地速均为正；质量单调下降；终止质量达到题设值。验证时检查升力平衡相对残差

```text
r_L = |L-mg|/(mg)
```

和能量方程相对残差

```text
r_E = |T-D-m dV/dt-mg/V dh/dt| / max(|T|, |D|, |m dV/dt|, |mg/V dh/dt|, eps).
```

固定终止质量意味着两种策略总燃油消耗都为

```text
m0-mf=10450 kg,
```

该指标没有策略区分度，主要比较时间、航程、最终高度和爬升率。
