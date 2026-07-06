# q3 必要条件与求解推导

## 1. 优化问题

状态、控制和目标为：

```text
z=(x,h,V,m),   u=(T,gamma)
min J=m0-m(tf)
```

动力学：

```text
f_x = V cos(gamma)+W(h)
f_h = V sin(gamma)
f_V = (T-D)/m - g sin(gamma)
f_m = -cT T Phi(V)
Phi(V)=1+beta(V-Vopt)^2
```

升力和阻力：

```text
CL = 2 m g cos(gamma)/(rho V^2 S)
CD = CD0 + k CL^2
D = 0.5 rho V^2 S CD
```

把阻力展开为：

```text
D = 0.5 rho V^2 S CD0 + 2 k m^2 g^2 cos^2(gamma)/(rho V^2 S)
```

该形式便于计算导数。

## 2. Hamilton 函数

```text
H = lambda_x [V cos(gamma)+W(h)]
  + lambda_h V sin(gamma)
  + lambda_V [(T-D)/m - g sin(gamma)]
  - lambda_m cT T Phi(V)
```

伴随方程：

```text
dot(lambda_x) = -partial H/partial x = 0
dot(lambda_h) = -partial H/partial h
dot(lambda_V) = -partial H/partial V
dot(lambda_m) = -partial H/partial m
```

其中：

```text
dot(lambda_h) = -lambda_x dW/dh + lambda_V (1/m) dD/dh
dot(lambda_V) = -lambda_x cos(gamma) - lambda_h sin(gamma)
                + lambda_V (1/m) dD/dV
                + lambda_m cT T dPhi/dV
dot(lambda_m) = lambda_V [(T-D)/m^2 + (1/m) dD/dm]
```

注意 `D` 依赖 `h,V,m,gamma`。

## 3. 阻力导数结构

令

```text
A = 0.5 S CD0
B = 2 k g^2 / S
D = A rho V^2 + B m^2 cos^2(gamma)/(rho V^2)
```

则：

```text
dD/dh = A V^2 drho/dh
        - B m^2 cos^2(gamma)/(rho^2 V^2) drho/dh

dD/dV = 2 A rho V
        - 2 B m^2 cos^2(gamma)/(rho V^3)

dD/dm = 2 B m cos^2(gamma)/(rho V^2)

dD/dgamma = -2 B m^2 sin(gamma) cos(gamma)/(rho V^2)
```

风场导数：

```text
W(h)=20+3e-5(h-10000)^2
dW/dh=6e-5(h-10000)
```

速度惩罚导数：

```text
dPhi/dV=2 beta (V-Vopt)
```

## 4. 控制驻值条件

推力控制：

```text
partial H/partial T = lambda_V/m - lambda_m cT Phi(V)
```

若 `T_min<T<T_max` 且变化率约束不激活，则：

```text
lambda_V/m - lambda_m cT Phi(V)=0
```

否则推力位于边界或由变化率约束的 KKT 乘子决定。

航迹角控制：

```text
partial H/partial gamma =
 -lambda_x V sin(gamma)
 +lambda_h V cos(gamma)
 +lambda_V[-(1/m)dD/dgamma - g cos(gamma)]
```

若 `|gamma|<gamma_max` 且变化率约束不激活，则上式为 0；否则满足边界控制或 KKT 条件。

## 5. 终端条件

主方案固定：

```text
x(tf)=Xf
h(tf)=h_f
V(tf)=V_f
```

终端质量自由，目标 `J=m0-m(tf)`，因此终端横截条件给出：

```text
lambda_m(tf) = partial J/partial m(tf) = -1
```

固定终端 `x,h,V` 的伴随终值由对应边界约束乘子决定。终端时间自由，且终端状态约束不显含时间时，应满足：

```text
H(tf)=0
```

若状态约束如高度、速度、马赫数或质量下限激活，则加入路径约束乘子并满足互补松弛：

```text
mu_i(t) >= 0,  c_i(z,u) <= 0,  mu_i c_i = 0
```

## 6. 直接配点转录

归一化时间：

```text
tau=t/tf,  dz/dtau = tf f(z,u)
```

节点变量：

```text
{x_i,h_i,V_i,m_i,T_i,gamma_i}_{i=0}^{N-1}, tf
```

梯形缺陷可写为：

```text
z_{i+1}-z_i - 0.5 Δtau tf [f(z_i,u_i)+f(z_{i+1},u_{i+1})] = 0
```

Hermite-Simpson 版本增加中点状态和控制，缺陷更高阶。第一版建议先用梯形或低节点 HS 验证可行性，再加密网格。

## 7. 能量高度分析

定义能量高度：

```text
E = h + V^2/(2g)
```

无风、点质量动力学下：

```text
dE/dt = dh/dt + V/g dV/dt
      = V sin(gamma) + V/g [(T-D)/m - g sin(gamma)]
      = (T-D)V/(m g)
```

航迹角项抵消，因此无风且目标/约束只依赖机械能时，可考虑能量高度降维。

降维成立条件：

- 无风，或风与高度无关且不改变单位航程油耗结构；
- 小航迹角；
- 目标和约束可由能量状态表示；
- 无独立高度、速度、马赫限制；
- 终端条件只约束总机械能。

有风时：

```text
dx/dt = V cos(gamma)+W(h)
```

单位航程油耗为：

```text
q_x = q_f/[V cos(gamma)+W(h)]
```

高度相关风速使相同能量高度下不同 `h,V` 组合不再等价，因此第三问有风主问题不能只靠能量高度降维。

## 8. 后续实现检查量

正式求解后必须保存：

- 动力学缺陷最大范数；
- 边界条件误差；
- 状态和控制约束最小余量；
- 燃油积分与质量亏损差；
- `partial H/partial T` 和 `partial H/partial gamma` 残差；
- Hamiltonian 沿程变化和 `H(tf)`；
- 网格加密目标变化。
