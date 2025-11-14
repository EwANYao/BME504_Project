# BME504_Project
BME504 project

## 第一个问题：CV和CC比较的话看Ith 并不看 Qth
1. 生理学传统：电流是兴奋的基础电生理学的经典模型将电流视为产生兴奋的直接驱动力。强度-时程曲线（Strength–Duration Curve）：由 $\text{Lapicque}$ (1907) 定义，其基础变量就是电流。$\text{Lapicque}$ 公式：$\mathbf{I}_{\text{th}}(\tau) = \mathbf{I}_{\mathbf{r}}\left(1+\frac{\tau_{\mathbf{c}}}{\tau}\right)$，其中 $\mathbf{I}_{\mathbf{r}}$（基电流）是电流阈值的绝对下限。实验的便利性： 在神经刺激实验中，恒电流（$\text{CC}$）刺激是最常见的模式。实验者可以精确控制和测量电极输出的电流强度。直接可比性： 实测的 $\mathbf{I}_{\text{th}}$ 可直接用于比较不同神经纤维、不同波形或不同生理条件下的兴奋性。


### 模型：代码用的是MRG-like simplified model
在 节点 (node) 上插入了 MRG 的 axnode.mod 机制
但是：

节间 (internode) 只用了一个被动机制 pas，而没有包括 MRG 的 myelin 电导、电容、轴向空间参数；

没有 MRG 原文里的 periaxonal space、flut、MYSA 等过渡段；

所有几何（节长、节间长、直径、通道密度缩放）都是脚本里人工设置的简化形式，而非论文表格中的多段结构。

点电流注入 + internode 长度随直径线性增加 + gnabar 缩放 α=0.8

IClamp 点注入电流：电流在节点内注入（不是电极外场）。

节点面积随直径增加：注入电流分布到更大的膜面积。

internode 长度随直径增加（internode_len = max(50, 100*d)）：节点间距变大。

gnabar 以 α=0.8 缩放：钠通道密度增加幅度低于面积增加幅度（因为面积 ~d²，但 gnabar ~d^0.8）

### 模型用的是单节点内注入电流（intracellular current injection）
经典文献中的“大直径更易激活”通常指外部电场刺激（extracellular field stimulation）
我的结果并不违背


### Ith = Ath * Icath_peak 

Ath​,阈值缩放因子,Threshold Scale Factor,通过二分法搜索得到的最小乘数因子，当施加到归一化单位波形上时，能够刚好触发轴突模型的动作电位 (AP) 兴奋。Ath​ 越小，表明刺激波形的效率越高。
Icath_peak​,单位波形阴极峰值,Cathodic Peak Current of Unit Waveform,归一化电流单位波形 (InA_unit​) 中，具有最大绝对值的阴极相（负电流，即激发相）峰值电流。该值通常以安培 (A) 为单位计算，用于确定实际的阈值电流强度。
Ith​,阈值峰值电流,Threshold Peak Current,触发动作电位 (AP) 所需的实际最小阴极峰值电流。计算公式为：Ith​=Ath​×Icath_peak​ Ith​ 越小，表明激活 AP 越容易。




### 创新点
🔹 代表性文献

McIntyre, Richardson, & Grill, 2002, IEEE Trans. Biomed. Eng.

建立了 MRG 模型，系统研究了外部电场刺激下不同直径的阈值。结论：在外场刺激下，大直径纤维阈值更低（更容易激活）。
但他们主要用的是 extracellular stimulation，而不是点电流注入。

Rattay, 1989, 1999, 2000 系列论文

用电缆模型分析外电场的膜电位分布与激发条件。
同样是外场耦合型刺激，没有电流注入。

Howells et al., 2012 (J. Neural Eng.)

扩展了 MRG 模型，分析了直径、节点电性变化、钠通道分布对阈值的影响。
依然是外场刺激。

➡️ 你的不同点：
你采用了IClamp 点注入方式（内注入），并且让 internode 长度、gnabar 等随直径变化，这在 MRG 类研究中极少出现。
多数论文只做过外场条件下的 scaling，几乎没人系统量化“电流注入条件下阈值 vs 直径”的关系



### 结果分析
CC（方波）仍然比 CV（ETI）更有效很多，尤其在大直径处 CV 的 Ith 飙升至几百 µA，而 CC 仅几十 µA。
ETI（CV，电压经 Randles 滤波变成电流）显著降低了刺激的“瞬时阴极有效性”，表现为 在小直径时差别小，但随直径增大 ETI 会显著提高阈值电流 Ith
#### CC和CV倍数对比
直径 1–6 µm：Ith_CV / Ith_CC ≈ 0.9 – 1.2（≈ 无差别）

直径 8 µm：≈ 2.4×（CV ≈ 60 µA vs CC ≈ 25 µA）

直径 10 µm：≈ 4.5×（CV ≈ 160 µA vs CC ≈ 35 µA）

直径 12 µm：≈ 4.                                         0 – 5.0×（CV ≈ 350–480 µA vs CC ≈ 75–95 µA）

#### 双相情况阴极和阳极先结果对比
阴极相（负电流） → 膜外变负、膜内变正 → 膜去极化，有利于动作电位产生。

阳极相（正电流） → 膜外变正、膜内变负 → 膜超极化，抑制兴奋性。
因此：

先阴极 → 一上来就去极化 → 容易激活；
先阳极 → 一开始超极化 → 钠通道部分失活、膜更稳定 → 需要更大阴极电流才能“反超”这个抑制。



## 分析Qth 
为什么CC更大

CC 的 Qₜₕ 绝对值更大，是因为恒流方波在阈值时持续时间更长、波形更“宽”，带来的总电荷积更大；
而 CV 波形经 ETI 滤波后阴极峰虽短、幅度高，但尾部迅速衰减，总电荷积小。

Qth（Threshold charge）
→ 是波形的积分面积：Qth = A_th × ∫ I_unit dt。
→ 同样与 A_th 成正比