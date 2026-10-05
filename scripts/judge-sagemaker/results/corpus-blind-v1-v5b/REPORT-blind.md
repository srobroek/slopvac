# Blind human-versus-generated report: blind-20261003-v1

Documents: {'generated': 399, 'human': 200}. Findings: 24703. Items: {'finding-confirmation': 21872, 'semantic-detection': 87395}. Lint: /Users/sjors/tmp/worktrees/slopvac/lint-main-ca941af at ca941af16a.

AUC is P(generated scores above human), ties counted one half; 0.5 is no separation. The 95% CI is a cluster bootstrap over human sources with their generated matches (2000 resamples, seed 17). The paired win rate compares each generated document with its own human source. Judged scores use raw served probabilities with threshold 0.5. Rates are per 100 words.

## Separation

| score | human docs | generated docs | human mean | generated mean | AUC | 95% CI | paired win rate |
|---|---|---|---|---|---|---|---|
| lint rate (lint only) | 200 | 399 | 6.253 | 6.741 | 0.526 | [0.472, 0.578] | 0.529 |
| confirmed rate, kev-0.8b | 200 | 399 | 0.065 | 0.058 | 0.482 | [0.451, 0.512] | 0.480 |
| semantic yes rate, kev-0.8b | 200 | 399 | 0.010 | 0.008 | 0.516 | [0.478, 0.556] | 0.513 |
| semantic mean p, kev-0.8b | 200 | 399 | 0.234 | 0.239 | 0.357 | [0.309, 0.407] | 0.308 |
| confirmed rate, kev-0.8b-ft-s17 | 200 | 399 | 3.602 | 4.590 | 0.606 | [0.559, 0.653] | 0.604 |
| semantic yes rate, kev-0.8b-ft-s17 | 200 | 399 | 0.021 | 0.033 | 0.700 | [0.654, 0.747] | 0.716 |
| semantic mean p, kev-0.8b-ft-s17 | 200 | 399 | 0.063 | 0.079 | 0.648 | [0.603, 0.692] | 0.667 |
| confirmed rate, kev-0.8b-ft-s18 | 200 | 399 | 3.472 | 4.373 | 0.594 | [0.546, 0.644] | 0.586 |
| semantic yes rate, kev-0.8b-ft-s18 | 200 | 399 | 0.022 | 0.033 | 0.694 | [0.651, 0.737] | 0.722 |
| semantic mean p, kev-0.8b-ft-s18 | 200 | 399 | 0.070 | 0.085 | 0.634 | [0.591, 0.678] | 0.659 |
| confirmed rate, kev-0.8b-ft-s19 | 200 | 399 | 3.440 | 4.286 | 0.588 | [0.538, 0.635] | 0.584 |
| semantic yes rate, kev-0.8b-ft-s19 | 200 | 399 | 0.019 | 0.032 | 0.690 | [0.643, 0.734] | 0.708 |
| semantic mean p, kev-0.8b-ft-s19 | 200 | 399 | 0.059 | 0.077 | 0.668 | [0.624, 0.712] | 0.697 |
| confirmed rate, kev-4b | 200 | 399 | 0.498 | 0.573 | 0.545 | [0.499, 0.588] | 0.554 |
| semantic yes rate, kev-4b | 200 | 399 | 0.021 | 0.047 | 0.809 | [0.774, 0.844] | 0.835 |
| semantic mean p, kev-4b | 200 | 399 | 0.244 | 0.277 | 0.585 | [0.541, 0.628] | 0.589 |
| confirmed rate, kev-4b-ft-s17 | 200 | 399 | 3.668 | 4.684 | 0.610 | [0.558, 0.658] | 0.609 |
| semantic yes rate, kev-4b-ft-s17 | 200 | 399 | 0.017 | 0.040 | 0.822 | [0.785, 0.857] | 0.836 |
| semantic mean p, kev-4b-ft-s17 | 200 | 399 | 0.046 | 0.076 | 0.795 | [0.755, 0.832] | 0.827 |
| confirmed rate, kev-4b-ft-s18 | 200 | 399 | 3.662 | 4.650 | 0.603 | [0.552, 0.651] | 0.586 |
| semantic yes rate, kev-4b-ft-s18 | 200 | 399 | 0.016 | 0.036 | 0.811 | [0.776, 0.845] | 0.831 |
| semantic mean p, kev-4b-ft-s18 | 200 | 399 | 0.039 | 0.064 | 0.767 | [0.727, 0.807] | 0.792 |
| confirmed rate, kev-4b-ft-s19 | 200 | 399 | 3.652 | 4.543 | 0.594 | [0.543, 0.642] | 0.594 |
| semantic yes rate, kev-4b-ft-s19 | 200 | 399 | 0.019 | 0.039 | 0.791 | [0.754, 0.828] | 0.811 |
| semantic mean p, kev-4b-ft-s19 | 200 | 399 | 0.045 | 0.069 | 0.751 | [0.711, 0.790] | 0.769 |
| confirmed rate, kev-9b | 200 | 399 | 3.093 | 3.265 | 0.515 | [0.463, 0.564] | 0.511 |
| semantic yes rate, kev-9b | 200 | 399 | 0.073 | 0.110 | 0.780 | [0.738, 0.820] | 0.803 |
| semantic mean p, kev-9b | 200 | 399 | 0.255 | 0.282 | 0.495 | [0.445, 0.544] | 0.521 |
| confirmed rate, kev-9b-ft-s17 | 200 | 399 | 3.728 | 4.669 | 0.606 | [0.556, 0.653] | 0.612 |
| semantic yes rate, kev-9b-ft-s17 | 200 | 399 | 0.017 | 0.035 | 0.794 | [0.756, 0.829] | 0.811 |
| semantic mean p, kev-9b-ft-s17 | 200 | 399 | 0.027 | 0.047 | 0.777 | [0.738, 0.815] | 0.792 |
| confirmed rate, kev-9b-ft-s18 | 200 | 399 | 3.742 | 4.792 | 0.619 | [0.569, 0.666] | 0.607 |
| semantic yes rate, kev-9b-ft-s18 | 200 | 399 | 0.015 | 0.033 | 0.810 | [0.773, 0.846] | 0.828 |
| semantic mean p, kev-9b-ft-s18 | 200 | 399 | 0.027 | 0.048 | 0.801 | [0.762, 0.838] | 0.817 |
| confirmed rate, kev-9b-ft-s19 | 200 | 399 | 3.742 | 4.742 | 0.612 | [0.564, 0.659] | 0.607 |
| semantic yes rate, kev-9b-ft-s19 | 200 | 399 | 0.016 | 0.032 | 0.799 | [0.759, 0.840] | 0.818 |
| semantic mean p, kev-9b-ft-s19 | 200 | 399 | 0.027 | 0.045 | 0.790 | [0.751, 0.828] | 0.812 |
| confirmed rate, laya-english | 200 | 399 | 0.939 | 1.261 | 0.562 | [0.520, 0.604] | 0.619 |
| semantic yes rate, laya-english | 200 | 399 | 0.357 | 0.580 | 0.769 | [0.731, 0.806] | 0.764 |
| semantic mean p, laya-english | 200 | 399 | 0.383 | 0.532 | 0.775 | [0.737, 0.811] | 0.782 |
| confirmed rate, laya-multilingual | 200 | 399 | 0.461 | 0.283 | 0.447 | [0.402, 0.491] | 0.444 |
| semantic yes rate, laya-multilingual | 200 | 399 | 0.611 | 0.745 | 0.612 | [0.567, 0.657] | 0.610 |
| semantic mean p, laya-multilingual | 200 | 399 | 0.561 | 0.684 | 0.623 | [0.577, 0.668] | 0.614 |
| confirmed rate, laya-typed-decisions | 200 | 399 | 0.692 | 0.398 | 0.440 | [0.409, 0.472] | 0.421 |
| semantic yes rate, laya-typed-decisions | 200 | 399 | 0.340 | 0.487 | 0.668 | [0.622, 0.711] | 0.649 |
| semantic mean p, laya-typed-decisions | 200 | 399 | 0.408 | 0.490 | 0.674 | [0.630, 0.715] | 0.667 |
| confirmed rate, v3-kev-0.8b-ft-s17 | 200 | 399 | 3.554 | 4.302 | 0.578 | [0.530, 0.623] | 0.589 |
| semantic yes rate, v3-kev-0.8b-ft-s17 | 200 | 399 | 0.021 | 0.022 | 0.566 | [0.521, 0.612] | 0.576 |
| semantic mean p, v3-kev-0.8b-ft-s17 | 200 | 399 | 0.104 | 0.111 | 0.550 | [0.504, 0.594] | 0.536 |
| confirmed rate, v3-kev-0.8b-ft-s18 | 200 | 399 | 3.528 | 4.373 | 0.589 | [0.541, 0.637] | 0.604 |
| semantic yes rate, v3-kev-0.8b-ft-s18 | 200 | 399 | 0.012 | 0.012 | 0.550 | [0.505, 0.599] | 0.560 |
| semantic mean p, v3-kev-0.8b-ft-s18 | 200 | 399 | 0.072 | 0.075 | 0.538 | [0.493, 0.583] | 0.521 |
| confirmed rate, v3-kev-0.8b-ft-s19 | 200 | 399 | 3.930 | 4.517 | 0.549 | [0.501, 0.597] | 0.539 |
| semantic yes rate, v3-kev-0.8b-ft-s19 | 200 | 399 | 0.015 | 0.016 | 0.569 | [0.525, 0.611] | 0.586 |
| semantic mean p, v3-kev-0.8b-ft-s19 | 200 | 399 | 0.068 | 0.067 | 0.515 | [0.469, 0.559] | 0.504 |
| confirmed rate, v3-kev-4b-ft-s17 | 200 | 399 | 3.698 | 4.642 | 0.601 | [0.550, 0.650] | 0.589 |
| semantic yes rate, v3-kev-4b-ft-s17 | 200 | 399 | 0.009 | 0.025 | 0.744 | [0.705, 0.782] | 0.771 |
| semantic mean p, v3-kev-4b-ft-s17 | 200 | 399 | 0.034 | 0.057 | 0.769 | [0.730, 0.805] | 0.802 |
| confirmed rate, v3-kev-4b-ft-s18 | 200 | 399 | 3.708 | 4.751 | 0.610 | [0.561, 0.658] | 0.609 |
| semantic yes rate, v3-kev-4b-ft-s18 | 200 | 399 | 0.012 | 0.027 | 0.732 | [0.694, 0.772] | 0.752 |
| semantic mean p, v3-kev-4b-ft-s18 | 200 | 399 | 0.039 | 0.060 | 0.750 | [0.709, 0.790] | 0.772 |
| confirmed rate, v3-kev-4b-ft-s19 | 200 | 399 | 3.958 | 4.837 | 0.595 | [0.544, 0.644] | 0.596 |
| semantic yes rate, v3-kev-4b-ft-s19 | 200 | 399 | 0.008 | 0.018 | 0.684 | [0.640, 0.725] | 0.707 |
| semantic mean p, v3-kev-4b-ft-s19 | 200 | 399 | 0.027 | 0.042 | 0.731 | [0.690, 0.770] | 0.754 |
| confirmed rate, v3-kev-9b-ft-s17 | 200 | 399 | 3.798 | 4.834 | 0.616 | [0.566, 0.662] | 0.617 |
| semantic yes rate, v3-kev-9b-ft-s17 | 200 | 399 | 0.018 | 0.037 | 0.816 | [0.777, 0.853] | 0.846 |
| semantic mean p, v3-kev-9b-ft-s17 | 200 | 399 | 0.044 | 0.065 | 0.760 | [0.717, 0.800] | 0.767 |
| confirmed rate, v3-kev-9b-ft-s18 | 200 | 399 | 3.718 | 4.786 | 0.622 | [0.574, 0.667] | 0.629 |
| semantic yes rate, v3-kev-9b-ft-s18 | 200 | 399 | 0.024 | 0.041 | 0.763 | [0.718, 0.805] | 0.764 |
| semantic mean p, v3-kev-9b-ft-s18 | 200 | 399 | 0.058 | 0.077 | 0.714 | [0.670, 0.760] | 0.724 |
| confirmed rate, v3-kev-9b-ft-s19 | 200 | 399 | 3.890 | 4.950 | 0.617 | [0.566, 0.663] | 0.614 |
| semantic yes rate, v3-kev-9b-ft-s19 | 200 | 399 | 0.015 | 0.027 | 0.780 | [0.740, 0.819] | 0.788 |
| semantic mean p, v3-kev-9b-ft-s19 | 200 | 399 | 0.040 | 0.055 | 0.720 | [0.678, 0.762] | 0.747 |

Prediction coverage per arm: {"kev-0.8b": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-0.8b-ft-s17": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-0.8b-ft-s18": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-0.8b-ft-s19": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-4b": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-4b-ft-s17": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-4b-ft-s18": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-4b-ft-s19": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-9b": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-9b-ft-s17": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-9b-ft-s18": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "kev-9b-ft-s19": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "laya-english": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "laya-multilingual": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "laya-typed-decisions": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "v3-kev-0.8b-ft-s17": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "v3-kev-0.8b-ft-s18": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "v3-kev-0.8b-ft-s19": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "v3-kev-4b-ft-s17": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "v3-kev-4b-ft-s18": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "v3-kev-4b-ft-s19": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "v3-kev-9b-ft-s17": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "v3-kev-9b-ft-s18": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}, "v3-kev-9b-ft-s19": {"items_predicted": 109267, "items_without_prediction": 0, "not_blind": 2345}}

## By genre

| genre / score | human docs | generated docs | human mean | generated mean | AUC | 95% CI | paired win rate |
|---|---|---|---|---|---|---|---|
| change-comms: lint rate | 40 | 80 | 5.295 | 9.216 | 0.788 | [0.710, 0.864] | 0.800 |
| change-comms: confirmed rate, kev-0.8b | 40 | 80 | 0.017 | 0.076 | 0.531 | [0.487, 0.581] | 0.531 |
| change-comms: semantic mean p, kev-0.8b | 40 | 80 | 0.250 | 0.236 | 0.305 | [0.222, 0.397] | 0.287 |
| change-comms: confirmed rate, kev-0.8b-ft-s17 | 40 | 80 | 3.140 | 6.786 | 0.790 | [0.712, 0.863] | 0.775 |
| change-comms: semantic mean p, kev-0.8b-ft-s17 | 40 | 80 | 0.070 | 0.095 | 0.770 | [0.664, 0.866] | 0.750 |
| change-comms: confirmed rate, kev-0.8b-ft-s18 | 40 | 80 | 2.959 | 6.579 | 0.795 | [0.718, 0.865] | 0.762 |
| change-comms: semantic mean p, kev-0.8b-ft-s18 | 40 | 80 | 0.079 | 0.107 | 0.777 | [0.680, 0.867] | 0.825 |
| change-comms: confirmed rate, kev-0.8b-ft-s19 | 40 | 80 | 3.011 | 6.400 | 0.784 | [0.705, 0.856] | 0.750 |
| change-comms: semantic mean p, kev-0.8b-ft-s19 | 40 | 80 | 0.071 | 0.100 | 0.777 | [0.679, 0.866] | 0.787 |
| change-comms: confirmed rate, kev-4b | 40 | 80 | 0.503 | 0.644 | 0.562 | [0.441, 0.675] | 0.569 |
| change-comms: semantic mean p, kev-4b | 40 | 80 | 0.265 | 0.267 | 0.543 | [0.445, 0.639] | 0.562 |
| change-comms: confirmed rate, kev-4b-ft-s17 | 40 | 80 | 3.106 | 7.231 | 0.840 | [0.762, 0.902] | 0.812 |
| change-comms: semantic mean p, kev-4b-ft-s17 | 40 | 80 | 0.043 | 0.083 | 0.923 | [0.851, 0.978] | 0.925 |
| change-comms: confirmed rate, kev-4b-ft-s18 | 40 | 80 | 3.091 | 7.207 | 0.839 | [0.764, 0.901] | 0.812 |
| change-comms: semantic mean p, kev-4b-ft-s18 | 40 | 80 | 0.035 | 0.074 | 0.911 | [0.842, 0.966] | 0.938 |
| change-comms: confirmed rate, kev-4b-ft-s19 | 40 | 80 | 3.000 | 6.976 | 0.834 | [0.756, 0.900] | 0.825 |
| change-comms: semantic mean p, kev-4b-ft-s19 | 40 | 80 | 0.042 | 0.076 | 0.893 | [0.818, 0.958] | 0.887 |
| change-comms: confirmed rate, kev-9b | 40 | 80 | 2.999 | 4.568 | 0.678 | [0.562, 0.779] | 0.613 |
| change-comms: semantic mean p, kev-9b | 40 | 80 | 0.274 | 0.278 | 0.594 | [0.484, 0.700] | 0.613 |
| change-comms: confirmed rate, kev-9b-ft-s17 | 40 | 80 | 3.160 | 6.887 | 0.816 | [0.736, 0.886] | 0.762 |
| change-comms: semantic mean p, kev-9b-ft-s17 | 40 | 80 | 0.024 | 0.054 | 0.912 | [0.839, 0.965] | 0.912 |
| change-comms: confirmed rate, kev-9b-ft-s18 | 40 | 80 | 3.336 | 7.193 | 0.812 | [0.733, 0.883] | 0.775 |
| change-comms: semantic mean p, kev-9b-ft-s18 | 40 | 80 | 0.024 | 0.058 | 0.931 | [0.856, 0.988] | 0.950 |
| change-comms: confirmed rate, kev-9b-ft-s19 | 40 | 80 | 3.130 | 6.973 | 0.819 | [0.743, 0.886] | 0.800 |
| change-comms: semantic mean p, kev-9b-ft-s19 | 40 | 80 | 0.024 | 0.052 | 0.910 | [0.844, 0.965] | 0.900 |
| change-comms: confirmed rate, laya-english | 40 | 80 | 2.001 | 3.404 | 0.621 | [0.545, 0.700] | 0.681 |
| change-comms: semantic mean p, laya-english | 40 | 80 | 0.466 | 0.536 | 0.692 | [0.599, 0.789] | 0.700 |
| change-comms: confirmed rate, laya-multilingual | 40 | 80 | 0.476 | 0.256 | 0.464 | [0.378, 0.554] | 0.444 |
| change-comms: semantic mean p, laya-multilingual | 40 | 80 | 0.626 | 0.613 | 0.475 | [0.374, 0.583] | 0.475 |
| change-comms: confirmed rate, laya-typed-decisions | 40 | 80 | 2.105 | 1.318 | 0.378 | [0.308, 0.452] | 0.319 |
| change-comms: semantic mean p, laya-typed-decisions | 40 | 80 | 0.477 | 0.461 | 0.420 | [0.314, 0.526] | 0.375 |
| change-comms: confirmed rate, v3-kev-0.8b-ft-s17 | 40 | 80 | 3.270 | 6.466 | 0.772 | [0.696, 0.843] | 0.762 |
| change-comms: semantic mean p, v3-kev-0.8b-ft-s17 | 40 | 80 | 0.101 | 0.117 | 0.642 | [0.530, 0.748] | 0.662 |
| change-comms: confirmed rate, v3-kev-0.8b-ft-s18 | 40 | 80 | 3.177 | 6.490 | 0.774 | [0.694, 0.849] | 0.750 |
| change-comms: semantic mean p, v3-kev-0.8b-ft-s18 | 40 | 80 | 0.083 | 0.096 | 0.649 | [0.544, 0.748] | 0.662 |
| change-comms: confirmed rate, v3-kev-0.8b-ft-s19 | 40 | 80 | 3.595 | 6.663 | 0.742 | [0.659, 0.822] | 0.725 |
| change-comms: semantic mean p, v3-kev-0.8b-ft-s19 | 40 | 80 | 0.073 | 0.079 | 0.591 | [0.475, 0.695] | 0.562 |
| change-comms: confirmed rate, v3-kev-4b-ft-s17 | 40 | 80 | 3.058 | 7.064 | 0.838 | [0.761, 0.901] | 0.800 |
| change-comms: semantic mean p, v3-kev-4b-ft-s17 | 40 | 80 | 0.039 | 0.081 | 0.929 | [0.878, 0.973] | 0.938 |
| change-comms: confirmed rate, v3-kev-4b-ft-s18 | 40 | 80 | 3.184 | 7.205 | 0.831 | [0.753, 0.896] | 0.800 |
| change-comms: semantic mean p, v3-kev-4b-ft-s18 | 40 | 80 | 0.045 | 0.079 | 0.874 | [0.803, 0.937] | 0.863 |
| change-comms: confirmed rate, v3-kev-4b-ft-s19 | 40 | 80 | 3.421 | 7.063 | 0.808 | [0.728, 0.879] | 0.800 |
| change-comms: semantic mean p, v3-kev-4b-ft-s19 | 40 | 80 | 0.031 | 0.056 | 0.847 | [0.771, 0.917] | 0.850 |
| change-comms: confirmed rate, v3-kev-9b-ft-s17 | 40 | 80 | 3.343 | 7.256 | 0.813 | [0.731, 0.882] | 0.787 |
| change-comms: semantic mean p, v3-kev-9b-ft-s17 | 40 | 80 | 0.046 | 0.074 | 0.877 | [0.795, 0.942] | 0.887 |
| change-comms: confirmed rate, v3-kev-9b-ft-s18 | 40 | 80 | 3.320 | 7.142 | 0.821 | [0.749, 0.886] | 0.812 |
| change-comms: semantic mean p, v3-kev-9b-ft-s18 | 40 | 80 | 0.059 | 0.088 | 0.822 | [0.726, 0.905] | 0.850 |
| change-comms: confirmed rate, v3-kev-9b-ft-s19 | 40 | 80 | 3.325 | 7.429 | 0.827 | [0.754, 0.893] | 0.825 |
| change-comms: semantic mean p, v3-kev-9b-ft-s19 | 40 | 80 | 0.041 | 0.061 | 0.838 | [0.752, 0.915] | 0.838 |
| consumer: lint rate | 40 | 80 | 5.571 | 5.937 | 0.555 | [0.458, 0.656] | 0.588 |
| consumer: confirmed rate, kev-0.8b | 40 | 80 | 0.034 | 0.019 | 0.438 | [0.363, 0.505] | 0.431 |
| consumer: semantic mean p, kev-0.8b | 40 | 80 | 0.259 | 0.234 | 0.249 | [0.174, 0.330] | 0.250 |
| consumer: confirmed rate, kev-0.8b-ft-s17 | 40 | 80 | 3.289 | 4.083 | 0.631 | [0.541, 0.725] | 0.650 |
| consumer: semantic mean p, kev-0.8b-ft-s17 | 40 | 80 | 0.069 | 0.083 | 0.665 | [0.572, 0.761] | 0.725 |
| consumer: confirmed rate, kev-0.8b-ft-s18 | 40 | 80 | 3.284 | 3.841 | 0.591 | [0.491, 0.696] | 0.637 |
| consumer: semantic mean p, kev-0.8b-ft-s18 | 40 | 80 | 0.068 | 0.081 | 0.667 | [0.576, 0.757] | 0.725 |
| consumer: confirmed rate, kev-0.8b-ft-s19 | 40 | 80 | 3.207 | 3.759 | 0.597 | [0.499, 0.695] | 0.613 |
| consumer: semantic mean p, kev-0.8b-ft-s19 | 40 | 80 | 0.058 | 0.076 | 0.686 | [0.586, 0.786] | 0.750 |
| consumer: confirmed rate, kev-4b | 40 | 80 | 0.357 | 0.530 | 0.616 | [0.512, 0.722] | 0.625 |
| consumer: semantic mean p, kev-4b | 40 | 80 | 0.287 | 0.289 | 0.528 | [0.418, 0.638] | 0.550 |
| consumer: confirmed rate, kev-4b-ft-s17 | 40 | 80 | 3.394 | 4.068 | 0.626 | [0.533, 0.720] | 0.650 |
| consumer: semantic mean p, kev-4b-ft-s17 | 40 | 80 | 0.043 | 0.074 | 0.897 | [0.841, 0.946] | 0.925 |
| consumer: confirmed rate, kev-4b-ft-s18 | 40 | 80 | 3.455 | 3.985 | 0.594 | [0.499, 0.692] | 0.613 |
| consumer: semantic mean p, kev-4b-ft-s18 | 40 | 80 | 0.034 | 0.058 | 0.835 | [0.743, 0.914] | 0.825 |
| consumer: confirmed rate, kev-4b-ft-s19 | 40 | 80 | 3.436 | 3.865 | 0.570 | [0.475, 0.666] | 0.600 |
| consumer: semantic mean p, kev-4b-ft-s19 | 40 | 80 | 0.039 | 0.063 | 0.822 | [0.728, 0.899] | 0.825 |
| consumer: confirmed rate, kev-9b | 40 | 80 | 2.728 | 2.775 | 0.502 | [0.402, 0.603] | 0.475 |
| consumer: semantic mean p, kev-9b | 40 | 80 | 0.296 | 0.294 | 0.468 | [0.352, 0.585] | 0.512 |
| consumer: confirmed rate, kev-9b-ft-s17 | 40 | 80 | 3.388 | 4.027 | 0.610 | [0.531, 0.696] | 0.675 |
| consumer: semantic mean p, kev-9b-ft-s17 | 40 | 80 | 0.023 | 0.042 | 0.833 | [0.757, 0.902] | 0.838 |
| consumer: confirmed rate, kev-9b-ft-s18 | 40 | 80 | 3.416 | 4.149 | 0.636 | [0.555, 0.719] | 0.650 |
| consumer: semantic mean p, kev-9b-ft-s18 | 40 | 80 | 0.024 | 0.044 | 0.864 | [0.778, 0.932] | 0.850 |
| consumer: confirmed rate, kev-9b-ft-s19 | 40 | 80 | 3.464 | 4.099 | 0.617 | [0.528, 0.704] | 0.625 |
| consumer: semantic mean p, kev-9b-ft-s19 | 40 | 80 | 0.027 | 0.043 | 0.845 | [0.760, 0.918] | 0.850 |
| consumer: confirmed rate, laya-english | 40 | 80 | 0.296 | 0.534 | 0.686 | [0.596, 0.773] | 0.681 |
| consumer: semantic mean p, laya-english | 40 | 80 | 0.407 | 0.527 | 0.788 | [0.692, 0.878] | 0.800 |
| consumer: confirmed rate, laya-multilingual | 40 | 80 | 0.198 | 0.149 | 0.468 | [0.369, 0.560] | 0.438 |
| consumer: semantic mean p, laya-multilingual | 40 | 80 | 0.741 | 0.774 | 0.574 | [0.453, 0.698] | 0.613 |
| consumer: confirmed rate, laya-typed-decisions | 40 | 80 | 0.087 | 0.112 | 0.500 | [0.427, 0.565] | 0.487 |
| consumer: semantic mean p, laya-typed-decisions | 40 | 80 | 0.477 | 0.512 | 0.673 | [0.559, 0.782] | 0.700 |
| consumer: confirmed rate, v3-kev-0.8b-ft-s17 | 40 | 80 | 3.265 | 3.855 | 0.601 | [0.506, 0.702] | 0.675 |
| consumer: semantic mean p, v3-kev-0.8b-ft-s17 | 40 | 80 | 0.112 | 0.115 | 0.551 | [0.450, 0.641] | 0.550 |
| consumer: confirmed rate, v3-kev-0.8b-ft-s18 | 40 | 80 | 3.274 | 3.800 | 0.599 | [0.505, 0.696] | 0.637 |
| consumer: semantic mean p, v3-kev-0.8b-ft-s18 | 40 | 80 | 0.078 | 0.076 | 0.509 | [0.415, 0.602] | 0.463 |
| consumer: confirmed rate, v3-kev-0.8b-ft-s19 | 40 | 80 | 3.613 | 3.936 | 0.545 | [0.453, 0.646] | 0.588 |
| consumer: semantic mean p, v3-kev-0.8b-ft-s19 | 40 | 80 | 0.075 | 0.071 | 0.493 | [0.401, 0.587] | 0.537 |
| consumer: confirmed rate, v3-kev-4b-ft-s17 | 40 | 80 | 3.567 | 3.958 | 0.574 | [0.481, 0.672] | 0.588 |
| consumer: semantic mean p, v3-kev-4b-ft-s17 | 40 | 80 | 0.031 | 0.051 | 0.843 | [0.775, 0.912] | 0.925 |
| consumer: confirmed rate, v3-kev-4b-ft-s18 | 40 | 80 | 3.546 | 4.168 | 0.600 | [0.513, 0.694] | 0.662 |
| consumer: semantic mean p, v3-kev-4b-ft-s18 | 40 | 80 | 0.038 | 0.059 | 0.816 | [0.731, 0.896] | 0.850 |
| consumer: confirmed rate, v3-kev-4b-ft-s19 | 40 | 80 | 3.730 | 4.246 | 0.581 | [0.494, 0.673] | 0.600 |
| consumer: semantic mean p, v3-kev-4b-ft-s19 | 40 | 80 | 0.026 | 0.040 | 0.772 | [0.681, 0.861] | 0.812 |
| consumer: confirmed rate, v3-kev-9b-ft-s17 | 40 | 80 | 3.364 | 4.101 | 0.633 | [0.546, 0.728] | 0.650 |
| consumer: semantic mean p, v3-kev-9b-ft-s17 | 40 | 80 | 0.053 | 0.069 | 0.723 | [0.631, 0.814] | 0.750 |
| consumer: confirmed rate, v3-kev-9b-ft-s18 | 40 | 80 | 3.413 | 4.133 | 0.632 | [0.550, 0.716] | 0.662 |
| consumer: semantic mean p, v3-kev-9b-ft-s18 | 40 | 80 | 0.073 | 0.084 | 0.698 | [0.605, 0.794] | 0.738 |
| consumer: confirmed rate, v3-kev-9b-ft-s19 | 40 | 80 | 3.545 | 4.252 | 0.618 | [0.530, 0.713] | 0.662 |
| consumer: semantic mean p, v3-kev-9b-ft-s19 | 40 | 80 | 0.044 | 0.058 | 0.730 | [0.647, 0.810] | 0.787 |
| informal: lint rate | 40 | 80 | 6.395 | 5.854 | 0.428 | [0.307, 0.561] | 0.450 |
| informal: confirmed rate, kev-0.8b | 40 | 80 | 0.039 | 0.005 | 0.500 | [0.497, 0.500] | 0.487 |
| informal: semantic mean p, kev-0.8b | 40 | 80 | 0.270 | 0.239 | 0.235 | [0.159, 0.307] | 0.125 |
| informal: confirmed rate, kev-0.8b-ft-s17 | 40 | 80 | 3.336 | 3.483 | 0.524 | [0.409, 0.647] | 0.575 |
| informal: semantic mean p, kev-0.8b-ft-s17 | 40 | 80 | 0.079 | 0.072 | 0.453 | [0.367, 0.536] | 0.412 |
| informal: confirmed rate, kev-0.8b-ft-s18 | 40 | 80 | 3.225 | 3.218 | 0.509 | [0.395, 0.633] | 0.550 |
| informal: semantic mean p, kev-0.8b-ft-s18 | 40 | 80 | 0.094 | 0.083 | 0.434 | [0.328, 0.532] | 0.400 |
| informal: confirmed rate, kev-0.8b-ft-s19 | 40 | 80 | 3.203 | 3.168 | 0.490 | [0.373, 0.617] | 0.575 |
| informal: semantic mean p, kev-0.8b-ft-s19 | 40 | 80 | 0.071 | 0.066 | 0.498 | [0.388, 0.606] | 0.537 |
| informal: confirmed rate, kev-4b | 40 | 80 | 0.612 | 0.545 | 0.464 | [0.378, 0.556] | 0.469 |
| informal: semantic mean p, kev-4b | 40 | 80 | 0.266 | 0.267 | 0.512 | [0.420, 0.597] | 0.500 |
| informal: confirmed rate, kev-4b-ft-s17 | 40 | 80 | 3.757 | 3.517 | 0.477 | [0.369, 0.596] | 0.537 |
| informal: semantic mean p, kev-4b-ft-s17 | 40 | 80 | 0.068 | 0.085 | 0.658 | [0.561, 0.759] | 0.700 |
| informal: confirmed rate, kev-4b-ft-s18 | 40 | 80 | 3.674 | 3.453 | 0.466 | [0.354, 0.587] | 0.487 |
| informal: semantic mean p, kev-4b-ft-s18 | 40 | 80 | 0.054 | 0.073 | 0.651 | [0.552, 0.748] | 0.675 |
| informal: confirmed rate, kev-4b-ft-s19 | 40 | 80 | 3.631 | 3.419 | 0.476 | [0.368, 0.592] | 0.525 |
| informal: semantic mean p, kev-4b-ft-s19 | 40 | 80 | 0.065 | 0.082 | 0.652 | [0.553, 0.752] | 0.637 |
| informal: confirmed rate, kev-9b | 40 | 80 | 3.158 | 3.013 | 0.487 | [0.376, 0.601] | 0.588 |
| informal: semantic mean p, kev-9b | 40 | 80 | 0.283 | 0.284 | 0.502 | [0.404, 0.603] | 0.487 |
| informal: confirmed rate, kev-9b-ft-s17 | 40 | 80 | 3.851 | 3.618 | 0.470 | [0.357, 0.593] | 0.550 |
| informal: semantic mean p, kev-9b-ft-s17 | 40 | 80 | 0.039 | 0.053 | 0.672 | [0.564, 0.782] | 0.688 |
| informal: confirmed rate, kev-9b-ft-s18 | 40 | 80 | 3.760 | 3.727 | 0.515 | [0.391, 0.646] | 0.550 |
| informal: semantic mean p, kev-9b-ft-s18 | 40 | 80 | 0.040 | 0.055 | 0.681 | [0.573, 0.785] | 0.662 |
| informal: confirmed rate, kev-9b-ft-s19 | 40 | 80 | 3.775 | 3.668 | 0.491 | [0.374, 0.618] | 0.562 |
| informal: semantic mean p, kev-9b-ft-s19 | 40 | 80 | 0.036 | 0.049 | 0.682 | [0.588, 0.782] | 0.713 |
| informal: confirmed rate, laya-english | 40 | 80 | 0.682 | 0.633 | 0.503 | [0.394, 0.616] | 0.550 |
| informal: semantic mean p, laya-english | 40 | 80 | 0.411 | 0.472 | 0.647 | [0.562, 0.733] | 0.675 |
| informal: confirmed rate, laya-multilingual | 40 | 80 | 0.648 | 0.465 | 0.435 | [0.338, 0.535] | 0.487 |
| informal: semantic mean p, laya-multilingual | 40 | 80 | 0.479 | 0.531 | 0.554 | [0.454, 0.652] | 0.512 |
| informal: confirmed rate, laya-typed-decisions | 40 | 80 | 0.096 | 0.039 | 0.444 | [0.391, 0.494] | 0.450 |
| informal: semantic mean p, laya-typed-decisions | 40 | 80 | 0.403 | 0.425 | 0.602 | [0.521, 0.687] | 0.637 |
| informal: confirmed rate, v3-kev-0.8b-ft-s17 | 40 | 80 | 3.206 | 3.131 | 0.497 | [0.392, 0.609] | 0.512 |
| informal: semantic mean p, v3-kev-0.8b-ft-s17 | 40 | 80 | 0.140 | 0.115 | 0.386 | [0.302, 0.473] | 0.375 |
| informal: confirmed rate, v3-kev-0.8b-ft-s18 | 40 | 80 | 3.293 | 3.244 | 0.491 | [0.375, 0.616] | 0.575 |
| informal: semantic mean p, v3-kev-0.8b-ft-s18 | 40 | 80 | 0.087 | 0.066 | 0.356 | [0.268, 0.452] | 0.362 |
| informal: confirmed rate, v3-kev-0.8b-ft-s19 | 40 | 80 | 3.458 | 3.383 | 0.483 | [0.368, 0.602] | 0.500 |
| informal: semantic mean p, v3-kev-0.8b-ft-s19 | 40 | 80 | 0.084 | 0.059 | 0.313 | [0.235, 0.392] | 0.275 |
| informal: confirmed rate, v3-kev-4b-ft-s17 | 40 | 80 | 3.633 | 3.488 | 0.482 | [0.376, 0.595] | 0.537 |
| informal: semantic mean p, v3-kev-4b-ft-s17 | 40 | 80 | 0.041 | 0.056 | 0.703 | [0.608, 0.798] | 0.700 |
| informal: confirmed rate, v3-kev-4b-ft-s18 | 40 | 80 | 3.602 | 3.570 | 0.508 | [0.398, 0.622] | 0.537 |
| informal: semantic mean p, v3-kev-4b-ft-s18 | 40 | 80 | 0.047 | 0.058 | 0.615 | [0.499, 0.731] | 0.600 |
| informal: confirmed rate, v3-kev-4b-ft-s19 | 40 | 80 | 3.909 | 3.716 | 0.484 | [0.375, 0.605] | 0.550 |
| informal: semantic mean p, v3-kev-4b-ft-s19 | 40 | 80 | 0.033 | 0.042 | 0.633 | [0.529, 0.736] | 0.637 |
| informal: confirmed rate, v3-kev-9b-ft-s17 | 40 | 80 | 3.949 | 3.745 | 0.484 | [0.366, 0.608] | 0.537 |
| informal: semantic mean p, v3-kev-9b-ft-s17 | 40 | 80 | 0.050 | 0.071 | 0.779 | [0.676, 0.874] | 0.762 |
| informal: confirmed rate, v3-kev-9b-ft-s18 | 40 | 80 | 3.671 | 3.694 | 0.515 | [0.402, 0.637] | 0.562 |
| informal: semantic mean p, v3-kev-9b-ft-s18 | 40 | 80 | 0.063 | 0.075 | 0.682 | [0.564, 0.797] | 0.675 |
| informal: confirmed rate, v3-kev-9b-ft-s19 | 40 | 80 | 3.991 | 3.923 | 0.494 | [0.376, 0.619] | 0.562 |
| informal: semantic mean p, v3-kev-9b-ft-s19 | 40 | 80 | 0.049 | 0.061 | 0.696 | [0.584, 0.803] | 0.725 |
| internal: lint rate | 40 | 80 | 7.648 | 6.579 | 0.342 | [0.225, 0.463] | 0.338 |
| internal: confirmed rate, kev-0.8b | 40 | 80 | 0.162 | 0.159 | 0.547 | [0.453, 0.640] | 0.581 |
| internal: semantic mean p, kev-0.8b | 40 | 80 | 0.182 | 0.245 | 0.521 | [0.397, 0.642] | 0.450 |
| internal: confirmed rate, kev-0.8b-ft-s17 | 40 | 80 | 4.603 | 4.455 | 0.450 | [0.332, 0.572] | 0.400 |
| internal: semantic mean p, kev-0.8b-ft-s17 | 40 | 80 | 0.048 | 0.072 | 0.665 | [0.550, 0.778] | 0.675 |
| internal: confirmed rate, kev-0.8b-ft-s18 | 40 | 80 | 4.322 | 4.231 | 0.464 | [0.346, 0.575] | 0.400 |
| internal: semantic mean p, kev-0.8b-ft-s18 | 40 | 80 | 0.057 | 0.077 | 0.647 | [0.536, 0.756] | 0.637 |
| internal: confirmed rate, kev-0.8b-ft-s19 | 40 | 80 | 4.340 | 4.191 | 0.450 | [0.333, 0.570] | 0.400 |
| internal: semantic mean p, kev-0.8b-ft-s19 | 40 | 80 | 0.049 | 0.075 | 0.688 | [0.578, 0.789] | 0.675 |
| internal: confirmed rate, kev-4b | 40 | 80 | 0.475 | 0.563 | 0.563 | [0.457, 0.669] | 0.562 |
| internal: semantic mean p, kev-4b | 40 | 80 | 0.195 | 0.288 | 0.682 | [0.557, 0.809] | 0.675 |
| internal: confirmed rate, kev-4b-ft-s17 | 40 | 80 | 4.637 | 4.613 | 0.470 | [0.350, 0.591] | 0.438 |
| internal: semantic mean p, kev-4b-ft-s17 | 40 | 80 | 0.044 | 0.074 | 0.734 | [0.629, 0.827] | 0.762 |
| internal: confirmed rate, kev-4b-ft-s18 | 40 | 80 | 4.520 | 4.601 | 0.497 | [0.378, 0.621] | 0.450 |
| internal: semantic mean p, kev-4b-ft-s18 | 40 | 80 | 0.037 | 0.063 | 0.733 | [0.637, 0.827] | 0.787 |
| internal: confirmed rate, kev-4b-ft-s19 | 40 | 80 | 4.558 | 4.472 | 0.471 | [0.355, 0.595] | 0.463 |
| internal: semantic mean p, kev-4b-ft-s19 | 40 | 80 | 0.041 | 0.066 | 0.699 | [0.598, 0.795] | 0.738 |
| internal: confirmed rate, kev-9b | 40 | 80 | 3.339 | 3.389 | 0.485 | [0.370, 0.601] | 0.475 |
| internal: semantic mean p, kev-9b | 40 | 80 | 0.203 | 0.280 | 0.452 | [0.316, 0.583] | 0.463 |
| internal: confirmed rate, kev-9b-ft-s17 | 40 | 80 | 4.708 | 4.726 | 0.486 | [0.363, 0.613] | 0.475 |
| internal: semantic mean p, kev-9b-ft-s17 | 40 | 80 | 0.027 | 0.048 | 0.736 | [0.647, 0.822] | 0.787 |
| internal: confirmed rate, kev-9b-ft-s18 | 40 | 80 | 4.652 | 4.708 | 0.478 | [0.357, 0.605] | 0.450 |
| internal: semantic mean p, kev-9b-ft-s18 | 40 | 80 | 0.025 | 0.047 | 0.773 | [0.682, 0.857] | 0.812 |
| internal: confirmed rate, kev-9b-ft-s19 | 40 | 80 | 4.753 | 4.763 | 0.479 | [0.357, 0.601] | 0.450 |
| internal: semantic mean p, kev-9b-ft-s19 | 40 | 80 | 0.027 | 0.046 | 0.739 | [0.643, 0.834] | 0.787 |
| internal: confirmed rate, laya-english | 40 | 80 | 1.036 | 1.096 | 0.575 | [0.460, 0.690] | 0.619 |
| internal: semantic mean p, laya-english | 40 | 80 | 0.295 | 0.554 | 0.856 | [0.790, 0.916] | 0.875 |
| internal: confirmed rate, laya-multilingual | 40 | 80 | 0.407 | 0.400 | 0.556 | [0.443, 0.659] | 0.562 |
| internal: semantic mean p, laya-multilingual | 40 | 80 | 0.464 | 0.732 | 0.711 | [0.601, 0.810] | 0.738 |
| internal: confirmed rate, laya-typed-decisions | 40 | 80 | 0.965 | 0.400 | 0.423 | [0.332, 0.519] | 0.425 |
| internal: semantic mean p, laya-typed-decisions | 40 | 80 | 0.318 | 0.521 | 0.819 | [0.746, 0.888] | 0.825 |
| internal: confirmed rate, v3-kev-0.8b-ft-s17 | 40 | 80 | 4.556 | 4.320 | 0.438 | [0.315, 0.564] | 0.400 |
| internal: semantic mean p, v3-kev-0.8b-ft-s17 | 40 | 80 | 0.083 | 0.106 | 0.615 | [0.495, 0.729] | 0.550 |
| internal: confirmed rate, v3-kev-0.8b-ft-s18 | 40 | 80 | 4.379 | 4.406 | 0.481 | [0.366, 0.598] | 0.463 |
| internal: semantic mean p, v3-kev-0.8b-ft-s18 | 40 | 80 | 0.056 | 0.069 | 0.608 | [0.492, 0.723] | 0.550 |
| internal: confirmed rate, v3-kev-0.8b-ft-s19 | 40 | 80 | 4.960 | 4.483 | 0.402 | [0.285, 0.522] | 0.350 |
| internal: semantic mean p, v3-kev-0.8b-ft-s19 | 40 | 80 | 0.053 | 0.064 | 0.603 | [0.489, 0.717] | 0.575 |
| internal: confirmed rate, v3-kev-4b-ft-s17 | 40 | 80 | 4.617 | 4.640 | 0.488 | [0.367, 0.615] | 0.463 |
| internal: semantic mean p, v3-kev-4b-ft-s17 | 40 | 80 | 0.031 | 0.051 | 0.712 | [0.613, 0.811] | 0.725 |
| internal: confirmed rate, v3-kev-4b-ft-s18 | 40 | 80 | 4.617 | 4.751 | 0.504 | [0.379, 0.628] | 0.450 |
| internal: semantic mean p, v3-kev-4b-ft-s18 | 40 | 80 | 0.035 | 0.055 | 0.728 | [0.630, 0.825] | 0.787 |
| internal: confirmed rate, v3-kev-4b-ft-s19 | 40 | 80 | 4.805 | 4.836 | 0.488 | [0.368, 0.606] | 0.450 |
| internal: semantic mean p, v3-kev-4b-ft-s19 | 40 | 80 | 0.024 | 0.038 | 0.696 | [0.595, 0.800] | 0.688 |
| internal: confirmed rate, v3-kev-9b-ft-s17 | 40 | 80 | 4.685 | 4.847 | 0.506 | [0.383, 0.632] | 0.475 |
| internal: semantic mean p, v3-kev-9b-ft-s17 | 40 | 80 | 0.036 | 0.056 | 0.696 | [0.595, 0.791] | 0.675 |
| internal: confirmed rate, v3-kev-9b-ft-s18 | 40 | 80 | 4.711 | 4.811 | 0.490 | [0.365, 0.613] | 0.463 |
| internal: semantic mean p, v3-kev-9b-ft-s18 | 40 | 80 | 0.049 | 0.070 | 0.667 | [0.555, 0.779] | 0.675 |
| internal: confirmed rate, v3-kev-9b-ft-s19 | 40 | 80 | 4.842 | 4.917 | 0.484 | [0.360, 0.611] | 0.450 |
| internal: semantic mean p, v3-kev-9b-ft-s19 | 40 | 80 | 0.031 | 0.046 | 0.681 | [0.583, 0.780] | 0.675 |
| reference: lint rate | 40 | 79 | 6.358 | 6.109 | 0.440 | [0.336, 0.547] | 0.468 |
| reference: confirmed rate, kev-0.8b | 40 | 79 | 0.071 | 0.033 | 0.374 | [0.300, 0.443] | 0.367 |
| reference: semantic mean p, kev-0.8b | 40 | 79 | 0.209 | 0.243 | 0.437 | [0.295, 0.575] | 0.430 |
| reference: confirmed rate, kev-0.8b-ft-s17 | 40 | 79 | 3.643 | 4.137 | 0.579 | [0.479, 0.682] | 0.620 |
| reference: semantic mean p, kev-0.8b-ft-s17 | 40 | 79 | 0.050 | 0.074 | 0.720 | [0.607, 0.825] | 0.772 |
| reference: confirmed rate, kev-0.8b-ft-s18 | 40 | 79 | 3.570 | 3.989 | 0.562 | [0.459, 0.670] | 0.582 |
| reference: semantic mean p, kev-0.8b-ft-s18 | 40 | 79 | 0.054 | 0.076 | 0.717 | [0.608, 0.814] | 0.709 |
| reference: confirmed rate, kev-0.8b-ft-s19 | 40 | 79 | 3.439 | 3.909 | 0.576 | [0.467, 0.687] | 0.582 |
| reference: semantic mean p, kev-0.8b-ft-s19 | 40 | 79 | 0.044 | 0.069 | 0.753 | [0.654, 0.841] | 0.734 |
| reference: confirmed rate, kev-4b | 40 | 79 | 0.543 | 0.583 | 0.539 | [0.450, 0.625] | 0.544 |
| reference: semantic mean p, kev-4b | 40 | 79 | 0.209 | 0.275 | 0.676 | [0.561, 0.790] | 0.658 |
| reference: confirmed rate, kev-4b-ft-s17 | 40 | 79 | 3.447 | 3.982 | 0.586 | [0.487, 0.686] | 0.608 |
| reference: semantic mean p, kev-4b-ft-s17 | 40 | 79 | 0.034 | 0.067 | 0.827 | [0.734, 0.910] | 0.823 |
| reference: confirmed rate, kev-4b-ft-s18 | 40 | 79 | 3.569 | 3.994 | 0.566 | [0.465, 0.668] | 0.570 |
| reference: semantic mean p, kev-4b-ft-s18 | 40 | 79 | 0.036 | 0.054 | 0.764 | [0.656, 0.858] | 0.734 |
| reference: confirmed rate, kev-4b-ft-s19 | 40 | 79 | 3.637 | 3.979 | 0.555 | [0.449, 0.659] | 0.557 |
| reference: semantic mean p, kev-4b-ft-s19 | 40 | 79 | 0.038 | 0.058 | 0.771 | [0.671, 0.862] | 0.759 |
| reference: confirmed rate, kev-9b | 40 | 79 | 3.240 | 2.572 | 0.389 | [0.276, 0.508] | 0.405 |
| reference: semantic mean p, kev-9b | 40 | 79 | 0.218 | 0.271 | 0.509 | [0.381, 0.641] | 0.532 |
| reference: confirmed rate, kev-9b-ft-s17 | 40 | 79 | 3.534 | 4.079 | 0.588 | [0.481, 0.695] | 0.595 |
| reference: semantic mean p, kev-9b-ft-s17 | 40 | 79 | 0.024 | 0.037 | 0.780 | [0.678, 0.868] | 0.734 |
| reference: confirmed rate, kev-9b-ft-s18 | 40 | 79 | 3.549 | 4.177 | 0.603 | [0.499, 0.708] | 0.608 |
| reference: semantic mean p, kev-9b-ft-s18 | 40 | 79 | 0.021 | 0.038 | 0.784 | [0.686, 0.871] | 0.810 |
| reference: confirmed rate, kev-9b-ft-s19 | 40 | 79 | 3.589 | 4.198 | 0.598 | [0.496, 0.701] | 0.595 |
| reference: semantic mean p, kev-9b-ft-s19 | 40 | 79 | 0.021 | 0.036 | 0.828 | [0.741, 0.907] | 0.810 |
| reference: confirmed rate, laya-english | 40 | 79 | 0.681 | 0.630 | 0.524 | [0.406, 0.645] | 0.563 |
| reference: semantic mean p, laya-english | 40 | 79 | 0.335 | 0.572 | 0.862 | [0.787, 0.925] | 0.861 |
| reference: confirmed rate, laya-multilingual | 40 | 79 | 0.575 | 0.143 | 0.316 | [0.223, 0.409] | 0.285 |
| reference: semantic mean p, laya-multilingual | 40 | 79 | 0.498 | 0.771 | 0.752 | [0.643, 0.853] | 0.734 |
| reference: confirmed rate, laya-typed-decisions | 40 | 79 | 0.208 | 0.115 | 0.432 | [0.368, 0.489] | 0.424 |
| reference: semantic mean p, laya-typed-decisions | 40 | 79 | 0.367 | 0.528 | 0.814 | [0.721, 0.897] | 0.797 |
| reference: confirmed rate, v3-kev-0.8b-ft-s17 | 40 | 79 | 3.475 | 3.731 | 0.532 | [0.431, 0.642] | 0.595 |
| reference: semantic mean p, v3-kev-0.8b-ft-s17 | 40 | 79 | 0.084 | 0.100 | 0.582 | [0.462, 0.696] | 0.544 |
| reference: confirmed rate, v3-kev-0.8b-ft-s18 | 40 | 79 | 3.519 | 3.920 | 0.552 | [0.448, 0.661] | 0.595 |
| reference: semantic mean p, v3-kev-0.8b-ft-s18 | 40 | 79 | 0.058 | 0.070 | 0.601 | [0.482, 0.715] | 0.570 |
| reference: confirmed rate, v3-kev-0.8b-ft-s19 | 40 | 79 | 4.023 | 4.114 | 0.509 | [0.412, 0.609] | 0.532 |
| reference: semantic mean p, v3-kev-0.8b-ft-s19 | 40 | 79 | 0.056 | 0.063 | 0.582 | [0.465, 0.700] | 0.570 |
| reference: confirmed rate, v3-kev-4b-ft-s17 | 40 | 79 | 3.616 | 4.051 | 0.570 | [0.470, 0.668] | 0.557 |
| reference: semantic mean p, v3-kev-4b-ft-s17 | 40 | 79 | 0.028 | 0.045 | 0.743 | [0.635, 0.841] | 0.722 |
| reference: confirmed rate, v3-kev-4b-ft-s18 | 40 | 79 | 3.590 | 4.053 | 0.560 | [0.468, 0.656] | 0.595 |
| reference: semantic mean p, v3-kev-4b-ft-s18 | 40 | 79 | 0.030 | 0.051 | 0.764 | [0.658, 0.854] | 0.759 |
| reference: confirmed rate, v3-kev-4b-ft-s19 | 40 | 79 | 3.926 | 4.318 | 0.564 | [0.464, 0.664] | 0.582 |
| reference: semantic mean p, v3-kev-4b-ft-s19 | 40 | 79 | 0.020 | 0.034 | 0.757 | [0.658, 0.846] | 0.785 |
| reference: confirmed rate, v3-kev-9b-ft-s17 | 40 | 79 | 3.650 | 4.212 | 0.603 | [0.500, 0.707] | 0.633 |
| reference: semantic mean p, v3-kev-9b-ft-s17 | 40 | 79 | 0.036 | 0.056 | 0.770 | [0.668, 0.869] | 0.759 |
| reference: confirmed rate, v3-kev-9b-ft-s18 | 40 | 79 | 3.476 | 4.143 | 0.609 | [0.507, 0.712] | 0.646 |
| reference: semantic mean p, v3-kev-9b-ft-s18 | 40 | 79 | 0.047 | 0.067 | 0.717 | [0.612, 0.821] | 0.684 |
| reference: confirmed rate, v3-kev-9b-ft-s19 | 40 | 79 | 3.749 | 4.218 | 0.579 | [0.472, 0.685] | 0.570 |
| reference: semantic mean p, v3-kev-9b-ft-s19 | 40 | 79 | 0.037 | 0.048 | 0.695 | [0.586, 0.808] | 0.709 |

## By generator vendor

| generator vendor / score | human docs | generated docs | human mean | generated mean | AUC | 95% CI | paired win rate |
|---|---|---|---|---|---|---|---|
| amazon: lint rate | 45 | 45 | 6.092 | 7.862 | 0.638 | [0.523, 0.758] | 0.578 |
| amazon: confirmed rate, kev-0.8b | 45 | 45 | 0.090 | 0.043 | 0.415 | [0.342, 0.490] | 0.433 |
| amazon: semantic mean p, kev-0.8b | 45 | 45 | 0.230 | 0.238 | 0.336 | [0.208, 0.465] | 0.378 |
| amazon: confirmed rate, kev-0.8b-ft-s17 | 45 | 45 | 3.483 | 5.974 | 0.769 | [0.672, 0.864] | 0.711 |
| amazon: semantic mean p, kev-0.8b-ft-s17 | 45 | 45 | 0.063 | 0.081 | 0.658 | [0.564, 0.750] | 0.689 |
| amazon: confirmed rate, kev-0.8b-ft-s18 | 45 | 45 | 3.298 | 5.857 | 0.774 | [0.680, 0.866] | 0.711 |
| amazon: semantic mean p, kev-0.8b-ft-s18 | 45 | 45 | 0.071 | 0.091 | 0.682 | [0.586, 0.775] | 0.711 |
| amazon: confirmed rate, kev-0.8b-ft-s19 | 45 | 45 | 3.268 | 5.700 | 0.780 | [0.682, 0.873] | 0.756 |
| amazon: semantic mean p, kev-0.8b-ft-s19 | 45 | 45 | 0.058 | 0.082 | 0.698 | [0.618, 0.782] | 0.756 |
| amazon: confirmed rate, kev-4b | 45 | 45 | 0.563 | 0.859 | 0.621 | [0.499, 0.741] | 0.656 |
| amazon: semantic mean p, kev-4b | 45 | 45 | 0.240 | 0.277 | 0.584 | [0.470, 0.691] | 0.578 |
| amazon: confirmed rate, kev-4b-ft-s17 | 45 | 45 | 3.429 | 5.739 | 0.760 | [0.664, 0.857] | 0.756 |
| amazon: semantic mean p, kev-4b-ft-s17 | 45 | 45 | 0.053 | 0.081 | 0.745 | [0.647, 0.843] | 0.800 |
| amazon: confirmed rate, kev-4b-ft-s18 | 45 | 45 | 3.515 | 5.835 | 0.752 | [0.650, 0.850] | 0.733 |
| amazon: semantic mean p, kev-4b-ft-s18 | 45 | 45 | 0.048 | 0.070 | 0.727 | [0.623, 0.829] | 0.822 |
| amazon: confirmed rate, kev-4b-ft-s19 | 45 | 45 | 3.442 | 5.722 | 0.757 | [0.652, 0.853] | 0.711 |
| amazon: semantic mean p, kev-4b-ft-s19 | 45 | 45 | 0.051 | 0.073 | 0.723 | [0.618, 0.822] | 0.778 |
| amazon: confirmed rate, kev-9b | 45 | 45 | 3.035 | 3.511 | 0.566 | [0.443, 0.693] | 0.511 |
| amazon: semantic mean p, kev-9b | 45 | 45 | 0.247 | 0.281 | 0.512 | [0.406, 0.626] | 0.578 |
| amazon: confirmed rate, kev-9b-ft-s17 | 45 | 45 | 3.553 | 5.790 | 0.740 | [0.641, 0.832] | 0.711 |
| amazon: semantic mean p, kev-9b-ft-s17 | 45 | 45 | 0.035 | 0.054 | 0.756 | [0.655, 0.851] | 0.756 |
| amazon: confirmed rate, kev-9b-ft-s18 | 45 | 45 | 3.608 | 5.849 | 0.753 | [0.650, 0.847] | 0.711 |
| amazon: semantic mean p, kev-9b-ft-s18 | 45 | 45 | 0.031 | 0.054 | 0.770 | [0.676, 0.862] | 0.756 |
| amazon: confirmed rate, kev-9b-ft-s19 | 45 | 45 | 3.536 | 5.961 | 0.768 | [0.669, 0.862] | 0.756 |
| amazon: semantic mean p, kev-9b-ft-s19 | 45 | 45 | 0.030 | 0.048 | 0.761 | [0.655, 0.853] | 0.778 |
| amazon: confirmed rate, laya-english | 45 | 45 | 0.884 | 1.542 | 0.561 | [0.460, 0.662] | 0.644 |
| amazon: semantic mean p, laya-english | 45 | 45 | 0.351 | 0.508 | 0.781 | [0.686, 0.867] | 0.844 |
| amazon: confirmed rate, laya-multilingual | 45 | 45 | 0.495 | 0.245 | 0.377 | [0.285, 0.477] | 0.367 |
| amazon: semantic mean p, laya-multilingual | 45 | 45 | 0.513 | 0.600 | 0.576 | [0.467, 0.683] | 0.556 |
| amazon: confirmed rate, laya-typed-decisions | 45 | 45 | 0.402 | 0.638 | 0.426 | [0.358, 0.497] | 0.400 |
| amazon: semantic mean p, laya-typed-decisions | 45 | 45 | 0.386 | 0.477 | 0.687 | [0.574, 0.790] | 0.644 |
| amazon: confirmed rate, v3-kev-0.8b-ft-s17 | 45 | 45 | 3.425 | 5.569 | 0.743 | [0.643, 0.838] | 0.689 |
| amazon: semantic mean p, v3-kev-0.8b-ft-s17 | 45 | 45 | 0.101 | 0.107 | 0.546 | [0.443, 0.649] | 0.556 |
| amazon: confirmed rate, v3-kev-0.8b-ft-s18 | 45 | 45 | 3.370 | 5.799 | 0.771 | [0.673, 0.863] | 0.756 |
| amazon: semantic mean p, v3-kev-0.8b-ft-s18 | 45 | 45 | 0.072 | 0.076 | 0.564 | [0.463, 0.669] | 0.578 |
| amazon: confirmed rate, v3-kev-0.8b-ft-s19 | 45 | 45 | 3.871 | 5.821 | 0.719 | [0.615, 0.820] | 0.689 |
| amazon: semantic mean p, v3-kev-0.8b-ft-s19 | 45 | 45 | 0.067 | 0.066 | 0.532 | [0.434, 0.634] | 0.556 |
| amazon: confirmed rate, v3-kev-4b-ft-s17 | 45 | 45 | 3.426 | 5.813 | 0.770 | [0.670, 0.864] | 0.733 |
| amazon: semantic mean p, v3-kev-4b-ft-s17 | 45 | 45 | 0.033 | 0.062 | 0.776 | [0.685, 0.866] | 0.800 |
| amazon: confirmed rate, v3-kev-4b-ft-s18 | 45 | 45 | 3.509 | 5.904 | 0.773 | [0.672, 0.863] | 0.733 |
| amazon: semantic mean p, v3-kev-4b-ft-s18 | 45 | 45 | 0.042 | 0.069 | 0.743 | [0.647, 0.840] | 0.756 |
| amazon: confirmed rate, v3-kev-4b-ft-s19 | 45 | 45 | 3.736 | 5.814 | 0.742 | [0.637, 0.845] | 0.711 |
| amazon: semantic mean p, v3-kev-4b-ft-s19 | 45 | 45 | 0.026 | 0.045 | 0.722 | [0.627, 0.818] | 0.756 |
| amazon: confirmed rate, v3-kev-9b-ft-s17 | 45 | 45 | 3.571 | 5.954 | 0.750 | [0.646, 0.848] | 0.711 |
| amazon: semantic mean p, v3-kev-9b-ft-s17 | 45 | 45 | 0.047 | 0.072 | 0.795 | [0.712, 0.876] | 0.822 |
| amazon: confirmed rate, v3-kev-9b-ft-s18 | 45 | 45 | 3.540 | 5.887 | 0.749 | [0.646, 0.848] | 0.733 |
| amazon: semantic mean p, v3-kev-9b-ft-s18 | 45 | 45 | 0.062 | 0.085 | 0.725 | [0.629, 0.819] | 0.711 |
| amazon: confirmed rate, v3-kev-9b-ft-s19 | 45 | 45 | 3.690 | 6.114 | 0.750 | [0.649, 0.844] | 0.689 |
| amazon: semantic mean p, v3-kev-9b-ft-s19 | 45 | 45 | 0.043 | 0.061 | 0.758 | [0.662, 0.845] | 0.756 |
| anthropic: lint rate | 41 | 41 | 6.070 | 6.939 | 0.586 | [0.457, 0.706] | 0.585 |
| anthropic: confirmed rate, kev-0.8b | 41 | 41 | 0.040 | 0.099 | 0.600 | [0.531, 0.668] | 0.598 |
| anthropic: semantic mean p, kev-0.8b | 41 | 41 | 0.215 | 0.241 | 0.463 | [0.336, 0.585] | 0.341 |
| anthropic: confirmed rate, kev-0.8b-ft-s17 | 41 | 41 | 3.217 | 4.667 | 0.684 | [0.568, 0.779] | 0.634 |
| anthropic: semantic mean p, kev-0.8b-ft-s17 | 41 | 41 | 0.061 | 0.082 | 0.714 | [0.624, 0.807] | 0.732 |
| anthropic: confirmed rate, kev-0.8b-ft-s18 | 41 | 41 | 3.130 | 4.370 | 0.648 | [0.523, 0.760] | 0.659 |
| anthropic: semantic mean p, kev-0.8b-ft-s18 | 41 | 41 | 0.068 | 0.088 | 0.667 | [0.570, 0.766] | 0.732 |
| anthropic: confirmed rate, kev-0.8b-ft-s19 | 41 | 41 | 3.165 | 4.361 | 0.642 | [0.519, 0.750] | 0.610 |
| anthropic: semantic mean p, kev-0.8b-ft-s19 | 41 | 41 | 0.055 | 0.077 | 0.685 | [0.590, 0.781] | 0.780 |
| anthropic: confirmed rate, kev-4b | 41 | 41 | 0.353 | 0.905 | 0.742 | [0.644, 0.836] | 0.829 |
| anthropic: semantic mean p, kev-4b | 41 | 41 | 0.222 | 0.280 | 0.719 | [0.618, 0.812] | 0.732 |
| anthropic: confirmed rate, kev-4b-ft-s17 | 41 | 41 | 3.456 | 4.918 | 0.649 | [0.529, 0.754] | 0.634 |
| anthropic: semantic mean p, kev-4b-ft-s17 | 41 | 41 | 0.041 | 0.076 | 0.851 | [0.778, 0.923] | 0.951 |
| anthropic: confirmed rate, kev-4b-ft-s18 | 41 | 41 | 3.377 | 4.842 | 0.656 | [0.537, 0.759] | 0.610 |
| anthropic: semantic mean p, kev-4b-ft-s18 | 41 | 41 | 0.034 | 0.064 | 0.804 | [0.711, 0.891] | 0.829 |
| anthropic: confirmed rate, kev-4b-ft-s19 | 41 | 41 | 3.368 | 4.806 | 0.658 | [0.538, 0.766] | 0.659 |
| anthropic: semantic mean p, kev-4b-ft-s19 | 41 | 41 | 0.041 | 0.066 | 0.763 | [0.667, 0.855] | 0.780 |
| anthropic: confirmed rate, kev-9b | 41 | 41 | 2.756 | 3.423 | 0.591 | [0.463, 0.717] | 0.634 |
| anthropic: semantic mean p, kev-9b | 41 | 41 | 0.235 | 0.281 | 0.561 | [0.444, 0.678] | 0.634 |
| anthropic: confirmed rate, kev-9b-ft-s17 | 41 | 41 | 3.403 | 4.821 | 0.666 | [0.548, 0.772] | 0.707 |
| anthropic: semantic mean p, kev-9b-ft-s17 | 41 | 41 | 0.022 | 0.045 | 0.833 | [0.749, 0.913] | 0.829 |
| anthropic: confirmed rate, kev-9b-ft-s18 | 41 | 41 | 3.367 | 4.981 | 0.689 | [0.566, 0.786] | 0.659 |
| anthropic: semantic mean p, kev-9b-ft-s18 | 41 | 41 | 0.023 | 0.044 | 0.808 | [0.719, 0.889] | 0.805 |
| anthropic: confirmed rate, kev-9b-ft-s19 | 41 | 41 | 3.393 | 4.902 | 0.679 | [0.566, 0.777] | 0.659 |
| anthropic: semantic mean p, kev-9b-ft-s19 | 41 | 41 | 0.023 | 0.041 | 0.813 | [0.720, 0.897] | 0.805 |
| anthropic: confirmed rate, laya-english | 41 | 41 | 0.928 | 1.538 | 0.654 | [0.553, 0.764] | 0.695 |
| anthropic: semantic mean p, laya-english | 41 | 41 | 0.360 | 0.525 | 0.760 | [0.654, 0.863] | 0.780 |
| anthropic: confirmed rate, laya-multilingual | 41 | 41 | 0.415 | 0.379 | 0.507 | [0.404, 0.617] | 0.537 |
| anthropic: semantic mean p, laya-multilingual | 41 | 41 | 0.479 | 0.708 | 0.738 | [0.634, 0.835] | 0.756 |
| anthropic: confirmed rate, laya-typed-decisions | 41 | 41 | 0.879 | 0.236 | 0.465 | [0.394, 0.534] | 0.476 |
| anthropic: semantic mean p, laya-typed-decisions | 41 | 41 | 0.372 | 0.475 | 0.663 | [0.553, 0.775] | 0.659 |
| anthropic: confirmed rate, v3-kev-0.8b-ft-s17 | 41 | 41 | 3.220 | 4.438 | 0.645 | [0.527, 0.750] | 0.659 |
| anthropic: semantic mean p, v3-kev-0.8b-ft-s17 | 41 | 41 | 0.097 | 0.115 | 0.595 | [0.487, 0.703] | 0.512 |
| anthropic: confirmed rate, v3-kev-0.8b-ft-s18 | 41 | 41 | 3.287 | 4.438 | 0.632 | [0.513, 0.736] | 0.634 |
| anthropic: semantic mean p, v3-kev-0.8b-ft-s18 | 41 | 41 | 0.067 | 0.077 | 0.557 | [0.444, 0.669] | 0.488 |
| anthropic: confirmed rate, v3-kev-0.8b-ft-s19 | 41 | 41 | 3.630 | 4.639 | 0.609 | [0.481, 0.717] | 0.537 |
| anthropic: semantic mean p, v3-kev-0.8b-ft-s19 | 41 | 41 | 0.061 | 0.067 | 0.552 | [0.433, 0.662] | 0.463 |
| anthropic: confirmed rate, v3-kev-4b-ft-s17 | 41 | 41 | 3.425 | 4.850 | 0.649 | [0.531, 0.751] | 0.610 |
| anthropic: semantic mean p, v3-kev-4b-ft-s17 | 41 | 41 | 0.031 | 0.054 | 0.811 | [0.728, 0.889] | 0.805 |
| anthropic: confirmed rate, v3-kev-4b-ft-s18 | 41 | 41 | 3.530 | 5.079 | 0.664 | [0.553, 0.767] | 0.683 |
| anthropic: semantic mean p, v3-kev-4b-ft-s18 | 41 | 41 | 0.035 | 0.059 | 0.811 | [0.725, 0.895] | 0.854 |
| anthropic: confirmed rate, v3-kev-4b-ft-s19 | 41 | 41 | 3.625 | 5.054 | 0.655 | [0.535, 0.759] | 0.634 |
| anthropic: semantic mean p, v3-kev-4b-ft-s19 | 41 | 41 | 0.025 | 0.042 | 0.778 | [0.685, 0.864] | 0.732 |
| anthropic: confirmed rate, v3-kev-9b-ft-s17 | 41 | 41 | 3.443 | 4.887 | 0.671 | [0.554, 0.773] | 0.659 |
| anthropic: semantic mean p, v3-kev-9b-ft-s17 | 41 | 41 | 0.039 | 0.063 | 0.787 | [0.682, 0.883] | 0.805 |
| anthropic: confirmed rate, v3-kev-9b-ft-s18 | 41 | 41 | 3.411 | 4.931 | 0.687 | [0.573, 0.783] | 0.707 |
| anthropic: semantic mean p, v3-kev-9b-ft-s18 | 41 | 41 | 0.051 | 0.077 | 0.768 | [0.662, 0.867] | 0.854 |
| anthropic: confirmed rate, v3-kev-9b-ft-s19 | 41 | 41 | 3.555 | 5.065 | 0.678 | [0.561, 0.778] | 0.659 |
| anthropic: semantic mean p, v3-kev-9b-ft-s19 | 41 | 41 | 0.036 | 0.054 | 0.789 | [0.695, 0.877] | 0.854 |
| deepseek: lint rate | 14 | 14 | 5.563 | 6.059 | 0.574 | [0.367, 0.776] | 0.571 |
| deepseek: confirmed rate, kev-0.8b | 14 | 14 | 0.124 | 0.037 | 0.388 | [0.273, 0.467] | 0.321 |
| deepseek: semantic mean p, kev-0.8b | 14 | 14 | 0.222 | 0.222 | 0.306 | [0.066, 0.571] | 0.286 |
| deepseek: confirmed rate, kev-0.8b-ft-s17 | 14 | 14 | 3.398 | 4.321 | 0.653 | [0.449, 0.847] | 0.714 |
| deepseek: semantic mean p, kev-0.8b-ft-s17 | 14 | 14 | 0.056 | 0.073 | 0.653 | [0.423, 0.847] | 0.571 |
| deepseek: confirmed rate, kev-0.8b-ft-s18 | 14 | 14 | 3.230 | 3.954 | 0.628 | [0.413, 0.816] | 0.571 |
| deepseek: semantic mean p, kev-0.8b-ft-s18 | 14 | 14 | 0.066 | 0.081 | 0.628 | [0.378, 0.821] | 0.429 |
| deepseek: confirmed rate, kev-0.8b-ft-s19 | 14 | 14 | 3.109 | 3.881 | 0.617 | [0.403, 0.816] | 0.643 |
| deepseek: semantic mean p, kev-0.8b-ft-s19 | 14 | 14 | 0.049 | 0.074 | 0.791 | [0.592, 0.944] | 0.714 |
| deepseek: confirmed rate, kev-4b | 14 | 14 | 0.462 | 0.324 | 0.434 | [0.245, 0.643] | 0.500 |
| deepseek: semantic mean p, kev-4b | 14 | 14 | 0.241 | 0.269 | 0.459 | [0.245, 0.673] | 0.429 |
| deepseek: confirmed rate, kev-4b-ft-s17 | 14 | 14 | 3.127 | 4.404 | 0.679 | [0.490, 0.857] | 0.786 |
| deepseek: semantic mean p, kev-4b-ft-s17 | 14 | 14 | 0.048 | 0.062 | 0.714 | [0.515, 0.893] | 0.786 |
| deepseek: confirmed rate, kev-4b-ft-s18 | 14 | 14 | 3.116 | 4.107 | 0.638 | [0.439, 0.832] | 0.643 |
| deepseek: semantic mean p, kev-4b-ft-s18 | 14 | 14 | 0.037 | 0.050 | 0.684 | [0.490, 0.867] | 0.786 |
| deepseek: confirmed rate, kev-4b-ft-s19 | 14 | 14 | 3.093 | 4.158 | 0.673 | [0.480, 0.857] | 0.714 |
| deepseek: semantic mean p, kev-4b-ft-s19 | 14 | 14 | 0.040 | 0.060 | 0.694 | [0.469, 0.888] | 0.714 |
| deepseek: confirmed rate, kev-9b | 14 | 14 | 2.710 | 2.976 | 0.594 | [0.429, 0.765] | 0.643 |
| deepseek: semantic mean p, kev-9b | 14 | 14 | 0.245 | 0.278 | 0.505 | [0.347, 0.668] | 0.500 |
| deepseek: confirmed rate, kev-9b-ft-s17 | 14 | 14 | 3.125 | 4.268 | 0.663 | [0.459, 0.852] | 0.643 |
| deepseek: semantic mean p, kev-9b-ft-s17 | 14 | 14 | 0.026 | 0.040 | 0.699 | [0.510, 0.883] | 0.857 |
| deepseek: confirmed rate, kev-9b-ft-s18 | 14 | 14 | 3.261 | 4.364 | 0.633 | [0.434, 0.832] | 0.714 |
| deepseek: semantic mean p, kev-9b-ft-s18 | 14 | 14 | 0.024 | 0.041 | 0.796 | [0.587, 0.959] | 0.786 |
| deepseek: confirmed rate, kev-9b-ft-s19 | 14 | 14 | 3.186 | 4.222 | 0.633 | [0.423, 0.832] | 0.643 |
| deepseek: semantic mean p, kev-9b-ft-s19 | 14 | 14 | 0.024 | 0.038 | 0.714 | [0.515, 0.903] | 0.786 |
| deepseek: confirmed rate, laya-english | 14 | 14 | 0.524 | 0.711 | 0.436 | [0.260, 0.597] | 0.464 |
| deepseek: semantic mean p, laya-english | 14 | 14 | 0.386 | 0.512 | 0.653 | [0.423, 0.857] | 0.643 |
| deepseek: confirmed rate, laya-multilingual | 14 | 14 | 0.426 | 0.164 | 0.383 | [0.189, 0.597] | 0.429 |
| deepseek: semantic mean p, laya-multilingual | 14 | 14 | 0.542 | 0.638 | 0.566 | [0.372, 0.760] | 0.571 |
| deepseek: confirmed rate, laya-typed-decisions | 14 | 14 | 0.146 | 0.273 | 0.500 | [0.393, 0.602] | 0.536 |
| deepseek: semantic mean p, laya-typed-decisions | 14 | 14 | 0.394 | 0.469 | 0.582 | [0.332, 0.786] | 0.429 |
| deepseek: confirmed rate, v3-kev-0.8b-ft-s17 | 14 | 14 | 3.128 | 3.752 | 0.602 | [0.418, 0.796] | 0.714 |
| deepseek: semantic mean p, v3-kev-0.8b-ft-s17 | 14 | 14 | 0.097 | 0.116 | 0.607 | [0.388, 0.816] | 0.571 |
| deepseek: confirmed rate, v3-kev-0.8b-ft-s18 | 14 | 14 | 3.127 | 4.166 | 0.643 | [0.444, 0.832] | 0.714 |
| deepseek: semantic mean p, v3-kev-0.8b-ft-s18 | 14 | 14 | 0.064 | 0.083 | 0.566 | [0.306, 0.801] | 0.500 |
| deepseek: confirmed rate, v3-kev-0.8b-ft-s19 | 14 | 14 | 3.585 | 3.862 | 0.551 | [0.362, 0.740] | 0.500 |
| deepseek: semantic mean p, v3-kev-0.8b-ft-s19 | 14 | 14 | 0.062 | 0.071 | 0.551 | [0.311, 0.776] | 0.571 |
| deepseek: confirmed rate, v3-kev-4b-ft-s17 | 14 | 14 | 3.116 | 4.363 | 0.668 | [0.490, 0.852] | 0.786 |
| deepseek: semantic mean p, v3-kev-4b-ft-s17 | 14 | 14 | 0.033 | 0.050 | 0.760 | [0.551, 0.929] | 0.714 |
| deepseek: confirmed rate, v3-kev-4b-ft-s18 | 14 | 14 | 3.146 | 4.162 | 0.643 | [0.454, 0.832] | 0.714 |
| deepseek: semantic mean p, v3-kev-4b-ft-s18 | 14 | 14 | 0.040 | 0.047 | 0.617 | [0.398, 0.827] | 0.714 |
| deepseek: confirmed rate, v3-kev-4b-ft-s19 | 14 | 14 | 3.498 | 4.452 | 0.643 | [0.454, 0.847] | 0.786 |
| deepseek: semantic mean p, v3-kev-4b-ft-s19 | 14 | 14 | 0.025 | 0.033 | 0.689 | [0.459, 0.903] | 0.786 |
| deepseek: confirmed rate, v3-kev-9b-ft-s17 | 14 | 14 | 3.201 | 4.521 | 0.679 | [0.490, 0.862] | 0.714 |
| deepseek: semantic mean p, v3-kev-9b-ft-s17 | 14 | 14 | 0.039 | 0.053 | 0.673 | [0.480, 0.862] | 0.786 |
| deepseek: confirmed rate, v3-kev-9b-ft-s18 | 14 | 14 | 3.136 | 4.364 | 0.648 | [0.454, 0.842] | 0.786 |
| deepseek: semantic mean p, v3-kev-9b-ft-s18 | 14 | 14 | 0.059 | 0.070 | 0.628 | [0.408, 0.837] | 0.643 |
| deepseek: confirmed rate, v3-kev-9b-ft-s19 | 14 | 14 | 3.408 | 4.618 | 0.663 | [0.480, 0.842] | 0.643 |
| deepseek: semantic mean p, v3-kev-9b-ft-s19 | 14 | 14 | 0.036 | 0.048 | 0.668 | [0.480, 0.867] | 0.786 |
| google: lint rate | 27 | 27 | 6.112 | 8.028 | 0.711 | [0.568, 0.838] | 0.667 |
| google: confirmed rate, kev-0.8b | 27 | 27 | 0.035 | 0.019 | 0.446 | [0.370, 0.523] | 0.444 |
| google: semantic mean p, kev-0.8b | 27 | 27 | 0.241 | 0.248 | 0.331 | [0.204, 0.462] | 0.333 |
| google: confirmed rate, kev-0.8b-ft-s17 | 27 | 27 | 3.768 | 6.053 | 0.785 | [0.665, 0.898] | 0.852 |
| google: semantic mean p, kev-0.8b-ft-s17 | 27 | 27 | 0.070 | 0.088 | 0.678 | [0.528, 0.822] | 0.704 |
| google: confirmed rate, kev-0.8b-ft-s18 | 27 | 27 | 3.598 | 5.753 | 0.783 | [0.660, 0.894] | 0.741 |
| google: semantic mean p, kev-0.8b-ft-s18 | 27 | 27 | 0.076 | 0.096 | 0.693 | [0.547, 0.835] | 0.704 |
| google: confirmed rate, kev-0.8b-ft-s19 | 27 | 27 | 3.564 | 5.666 | 0.775 | [0.646, 0.888] | 0.741 |
| google: semantic mean p, kev-0.8b-ft-s19 | 27 | 27 | 0.061 | 0.086 | 0.719 | [0.579, 0.850] | 0.778 |
| google: confirmed rate, kev-4b | 27 | 27 | 0.517 | 0.510 | 0.568 | [0.409, 0.727] | 0.593 |
| google: semantic mean p, kev-4b | 27 | 27 | 0.244 | 0.278 | 0.650 | [0.517, 0.783] | 0.630 |
| google: confirmed rate, kev-4b-ft-s17 | 27 | 27 | 3.657 | 5.927 | 0.800 | [0.684, 0.901] | 0.778 |
| google: semantic mean p, kev-4b-ft-s17 | 27 | 27 | 0.055 | 0.077 | 0.735 | [0.615, 0.849] | 0.778 |
| google: confirmed rate, kev-4b-ft-s18 | 27 | 27 | 3.642 | 5.633 | 0.796 | [0.669, 0.907] | 0.778 |
| google: semantic mean p, kev-4b-ft-s18 | 27 | 27 | 0.053 | 0.061 | 0.650 | [0.520, 0.776] | 0.630 |
| google: confirmed rate, kev-4b-ft-s19 | 27 | 27 | 3.690 | 5.689 | 0.786 | [0.664, 0.900] | 0.815 |
| google: semantic mean p, kev-4b-ft-s19 | 27 | 27 | 0.059 | 0.067 | 0.668 | [0.549, 0.781] | 0.630 |
| google: confirmed rate, kev-9b | 27 | 27 | 3.129 | 3.460 | 0.539 | [0.385, 0.695] | 0.630 |
| google: semantic mean p, kev-9b | 27 | 27 | 0.257 | 0.284 | 0.469 | [0.332, 0.610] | 0.519 |
| google: confirmed rate, kev-9b-ft-s17 | 27 | 27 | 3.702 | 5.799 | 0.800 | [0.676, 0.909] | 0.815 |
| google: semantic mean p, kev-9b-ft-s17 | 27 | 27 | 0.037 | 0.045 | 0.689 | [0.538, 0.824] | 0.704 |
| google: confirmed rate, kev-9b-ft-s18 | 27 | 27 | 3.754 | 5.933 | 0.783 | [0.658, 0.893] | 0.741 |
| google: semantic mean p, kev-9b-ft-s18 | 27 | 27 | 0.033 | 0.048 | 0.731 | [0.584, 0.864] | 0.704 |
| google: confirmed rate, kev-9b-ft-s19 | 27 | 27 | 3.729 | 5.871 | 0.796 | [0.671, 0.903] | 0.778 |
| google: semantic mean p, kev-9b-ft-s19 | 27 | 27 | 0.030 | 0.044 | 0.765 | [0.638, 0.886] | 0.741 |
| google: confirmed rate, laya-english | 27 | 27 | 1.262 | 1.660 | 0.615 | [0.473, 0.764] | 0.722 |
| google: semantic mean p, laya-english | 27 | 27 | 0.359 | 0.572 | 0.875 | [0.750, 0.970] | 0.852 |
| google: confirmed rate, laya-multilingual | 27 | 27 | 0.614 | 0.228 | 0.427 | [0.272, 0.576] | 0.389 |
| google: semantic mean p, laya-multilingual | 27 | 27 | 0.525 | 0.715 | 0.700 | [0.575, 0.818] | 0.593 |
| google: confirmed rate, laya-typed-decisions | 27 | 27 | 0.608 | 0.819 | 0.540 | [0.440, 0.639] | 0.500 |
| google: semantic mean p, laya-typed-decisions | 27 | 27 | 0.408 | 0.504 | 0.724 | [0.588, 0.850] | 0.741 |
| google: confirmed rate, v3-kev-0.8b-ft-s17 | 27 | 27 | 3.726 | 5.808 | 0.783 | [0.667, 0.889] | 0.741 |
| google: semantic mean p, v3-kev-0.8b-ft-s17 | 27 | 27 | 0.114 | 0.115 | 0.536 | [0.396, 0.683] | 0.593 |
| google: confirmed rate, v3-kev-0.8b-ft-s18 | 27 | 27 | 3.671 | 5.850 | 0.804 | [0.693, 0.907] | 0.815 |
| google: semantic mean p, v3-kev-0.8b-ft-s18 | 27 | 27 | 0.079 | 0.080 | 0.584 | [0.439, 0.734] | 0.630 |
| google: confirmed rate, v3-kev-0.8b-ft-s19 | 27 | 27 | 4.102 | 6.025 | 0.746 | [0.616, 0.861] | 0.704 |
| google: semantic mean p, v3-kev-0.8b-ft-s19 | 27 | 27 | 0.078 | 0.070 | 0.505 | [0.364, 0.652] | 0.556 |
| google: confirmed rate, v3-kev-4b-ft-s17 | 27 | 27 | 3.716 | 5.785 | 0.772 | [0.652, 0.882] | 0.778 |
| google: semantic mean p, v3-kev-4b-ft-s17 | 27 | 27 | 0.036 | 0.060 | 0.827 | [0.713, 0.925] | 0.889 |
| google: confirmed rate, v3-kev-4b-ft-s18 | 27 | 27 | 3.671 | 5.886 | 0.791 | [0.671, 0.900] | 0.852 |
| google: semantic mean p, v3-kev-4b-ft-s18 | 27 | 27 | 0.048 | 0.064 | 0.761 | [0.621, 0.888] | 0.741 |
| google: confirmed rate, v3-kev-4b-ft-s19 | 27 | 27 | 4.004 | 5.955 | 0.778 | [0.645, 0.892] | 0.741 |
| google: semantic mean p, v3-kev-4b-ft-s19 | 27 | 27 | 0.029 | 0.042 | 0.735 | [0.578, 0.870] | 0.630 |
| google: confirmed rate, v3-kev-9b-ft-s17 | 27 | 27 | 3.784 | 6.155 | 0.790 | [0.664, 0.901] | 0.741 |
| google: semantic mean p, v3-kev-9b-ft-s17 | 27 | 27 | 0.056 | 0.072 | 0.757 | [0.623, 0.882] | 0.667 |
| google: confirmed rate, v3-kev-9b-ft-s18 | 27 | 27 | 3.688 | 5.987 | 0.815 | [0.705, 0.914] | 0.778 |
| google: semantic mean p, v3-kev-9b-ft-s18 | 27 | 27 | 0.072 | 0.082 | 0.691 | [0.543, 0.833] | 0.667 |
| google: confirmed rate, v3-kev-9b-ft-s19 | 27 | 27 | 3.913 | 6.155 | 0.786 | [0.656, 0.901] | 0.778 |
| google: semantic mean p, v3-kev-9b-ft-s19 | 27 | 27 | 0.053 | 0.061 | 0.712 | [0.578, 0.841] | 0.704 |
| meta: lint rate | 44 | 44 | 6.231 | 7.639 | 0.574 | [0.442, 0.703] | 0.568 |
| meta: confirmed rate, kev-0.8b | 44 | 44 | 0.085 | 0.024 | 0.477 | [0.415, 0.542] | 0.477 |
| meta: semantic mean p, kev-0.8b | 44 | 44 | 0.235 | 0.240 | 0.372 | [0.263, 0.485] | 0.341 |
| meta: confirmed rate, kev-0.8b-ft-s17 | 44 | 44 | 3.557 | 6.163 | 0.736 | [0.617, 0.846] | 0.682 |
| meta: semantic mean p, kev-0.8b-ft-s17 | 44 | 44 | 0.068 | 0.072 | 0.561 | [0.433, 0.683] | 0.477 |
| meta: confirmed rate, kev-0.8b-ft-s18 | 44 | 44 | 3.462 | 6.111 | 0.748 | [0.636, 0.852] | 0.727 |
| meta: semantic mean p, kev-0.8b-ft-s18 | 44 | 44 | 0.075 | 0.079 | 0.566 | [0.443, 0.688] | 0.568 |
| meta: confirmed rate, kev-0.8b-ft-s19 | 44 | 44 | 3.341 | 5.782 | 0.738 | [0.627, 0.846] | 0.705 |
| meta: semantic mean p, kev-0.8b-ft-s19 | 44 | 44 | 0.065 | 0.069 | 0.585 | [0.461, 0.700] | 0.545 |
| meta: confirmed rate, kev-4b | 44 | 44 | 0.529 | 0.746 | 0.631 | [0.506, 0.747] | 0.693 |
| meta: semantic mean p, kev-4b | 44 | 44 | 0.250 | 0.277 | 0.526 | [0.426, 0.625] | 0.545 |
| meta: confirmed rate, kev-4b-ft-s17 | 44 | 44 | 3.481 | 6.037 | 0.735 | [0.627, 0.838] | 0.705 |
| meta: semantic mean p, kev-4b-ft-s17 | 44 | 44 | 0.049 | 0.075 | 0.736 | [0.635, 0.832] | 0.705 |
| meta: confirmed rate, kev-4b-ft-s18 | 44 | 44 | 3.505 | 6.003 | 0.723 | [0.614, 0.829] | 0.659 |
| meta: semantic mean p, kev-4b-ft-s18 | 44 | 44 | 0.041 | 0.066 | 0.751 | [0.652, 0.850] | 0.727 |
| meta: confirmed rate, kev-4b-ft-s19 | 44 | 44 | 3.544 | 5.958 | 0.716 | [0.606, 0.820] | 0.682 |
| meta: semantic mean p, kev-4b-ft-s19 | 44 | 44 | 0.048 | 0.069 | 0.716 | [0.611, 0.818] | 0.659 |
| meta: confirmed rate, kev-9b | 44 | 44 | 3.073 | 3.529 | 0.520 | [0.385, 0.654] | 0.523 |
| meta: semantic mean p, kev-9b | 44 | 44 | 0.257 | 0.280 | 0.449 | [0.326, 0.574] | 0.477 |
| meta: confirmed rate, kev-9b-ft-s17 | 44 | 44 | 3.513 | 5.973 | 0.725 | [0.613, 0.832] | 0.682 |
| meta: semantic mean p, kev-9b-ft-s17 | 44 | 44 | 0.031 | 0.052 | 0.761 | [0.659, 0.862] | 0.795 |
| meta: confirmed rate, kev-9b-ft-s18 | 44 | 44 | 3.569 | 6.067 | 0.724 | [0.607, 0.835] | 0.659 |
| meta: semantic mean p, kev-9b-ft-s18 | 44 | 44 | 0.031 | 0.053 | 0.783 | [0.673, 0.878] | 0.795 |
| meta: confirmed rate, kev-9b-ft-s19 | 44 | 44 | 3.591 | 5.966 | 0.718 | [0.604, 0.823] | 0.659 |
| meta: semantic mean p, kev-9b-ft-s19 | 44 | 44 | 0.032 | 0.048 | 0.768 | [0.663, 0.869] | 0.841 |
| meta: confirmed rate, laya-english | 44 | 44 | 1.044 | 1.639 | 0.582 | [0.489, 0.683] | 0.693 |
| meta: semantic mean p, laya-english | 44 | 44 | 0.380 | 0.549 | 0.799 | [0.712, 0.873] | 0.864 |
| meta: confirmed rate, laya-multilingual | 44 | 44 | 0.463 | 0.166 | 0.412 | [0.318, 0.513] | 0.398 |
| meta: semantic mean p, laya-multilingual | 44 | 44 | 0.584 | 0.718 | 0.633 | [0.515, 0.742] | 0.682 |
| meta: confirmed rate, laya-typed-decisions | 44 | 44 | 0.580 | 0.522 | 0.455 | [0.382, 0.531] | 0.455 |
| meta: semantic mean p, laya-typed-decisions | 44 | 44 | 0.421 | 0.497 | 0.668 | [0.554, 0.775] | 0.659 |
| meta: confirmed rate, v3-kev-0.8b-ft-s17 | 44 | 44 | 3.401 | 5.709 | 0.721 | [0.603, 0.832] | 0.682 |
| meta: semantic mean p, v3-kev-0.8b-ft-s17 | 44 | 44 | 0.118 | 0.098 | 0.416 | [0.301, 0.533] | 0.318 |
| meta: confirmed rate, v3-kev-0.8b-ft-s18 | 44 | 44 | 3.410 | 5.905 | 0.731 | [0.614, 0.844] | 0.727 |
| meta: semantic mean p, v3-kev-0.8b-ft-s18 | 44 | 44 | 0.080 | 0.070 | 0.450 | [0.330, 0.566] | 0.318 |
| meta: confirmed rate, v3-kev-0.8b-ft-s19 | 44 | 44 | 3.923 | 6.053 | 0.686 | [0.568, 0.804] | 0.682 |
| meta: semantic mean p, v3-kev-0.8b-ft-s19 | 44 | 44 | 0.079 | 0.059 | 0.405 | [0.291, 0.519] | 0.318 |
| meta: confirmed rate, v3-kev-4b-ft-s17 | 44 | 44 | 3.602 | 6.100 | 0.722 | [0.608, 0.827] | 0.636 |
| meta: semantic mean p, v3-kev-4b-ft-s17 | 44 | 44 | 0.035 | 0.059 | 0.770 | [0.678, 0.856] | 0.705 |
| meta: confirmed rate, v3-kev-4b-ft-s18 | 44 | 44 | 3.581 | 6.132 | 0.733 | [0.631, 0.834] | 0.727 |
| meta: semantic mean p, v3-kev-4b-ft-s18 | 44 | 44 | 0.039 | 0.065 | 0.763 | [0.668, 0.856] | 0.773 |
| meta: confirmed rate, v3-kev-4b-ft-s19 | 44 | 44 | 3.935 | 6.215 | 0.708 | [0.594, 0.816] | 0.636 |
| meta: semantic mean p, v3-kev-4b-ft-s19 | 44 | 44 | 0.029 | 0.044 | 0.720 | [0.619, 0.818] | 0.727 |
| meta: confirmed rate, v3-kev-9b-ft-s17 | 44 | 44 | 3.668 | 6.107 | 0.727 | [0.613, 0.835] | 0.682 |
| meta: semantic mean p, v3-kev-9b-ft-s17 | 44 | 44 | 0.050 | 0.072 | 0.739 | [0.636, 0.839] | 0.750 |
| meta: confirmed rate, v3-kev-9b-ft-s18 | 44 | 44 | 3.529 | 6.022 | 0.733 | [0.627, 0.834] | 0.659 |
| meta: semantic mean p, v3-kev-9b-ft-s18 | 44 | 44 | 0.062 | 0.082 | 0.710 | [0.598, 0.823] | 0.705 |
| meta: confirmed rate, v3-kev-9b-ft-s19 | 44 | 44 | 3.720 | 6.171 | 0.714 | [0.595, 0.828] | 0.659 |
| meta: semantic mean p, v3-kev-9b-ft-s19 | 44 | 44 | 0.045 | 0.058 | 0.710 | [0.602, 0.816] | 0.682 |
| minimax: lint rate | 28 | 28 | 6.431 | 5.351 | 0.335 | [0.205, 0.480] | 0.393 |
| minimax: confirmed rate, kev-0.8b | 28 | 28 | 0.038 | 0.042 | 0.489 | [0.379, 0.594] | 0.482 |
| minimax: semantic mean p, kev-0.8b | 28 | 28 | 0.232 | 0.238 | 0.352 | [0.198, 0.501] | 0.286 |
| minimax: confirmed rate, kev-0.8b-ft-s17 | 28 | 28 | 3.719 | 2.894 | 0.339 | [0.207, 0.476] | 0.286 |
| minimax: semantic mean p, kev-0.8b-ft-s17 | 28 | 28 | 0.055 | 0.087 | 0.707 | [0.598, 0.814] | 0.786 |
| minimax: confirmed rate, kev-0.8b-ft-s18 | 28 | 28 | 3.614 | 2.887 | 0.367 | [0.231, 0.510] | 0.321 |
| minimax: semantic mean p, kev-0.8b-ft-s18 | 28 | 28 | 0.064 | 0.085 | 0.661 | [0.546, 0.769] | 0.643 |
| minimax: confirmed rate, kev-0.8b-ft-s19 | 28 | 28 | 3.549 | 2.670 | 0.328 | [0.189, 0.473] | 0.286 |
| minimax: semantic mean p, kev-0.8b-ft-s19 | 28 | 28 | 0.053 | 0.081 | 0.742 | [0.638, 0.844] | 0.750 |
| minimax: confirmed rate, kev-4b | 28 | 28 | 0.442 | 0.400 | 0.517 | [0.392, 0.637] | 0.411 |
| minimax: semantic mean p, kev-4b | 28 | 28 | 0.240 | 0.271 | 0.561 | [0.415, 0.704] | 0.571 |
| minimax: confirmed rate, kev-4b-ft-s17 | 28 | 28 | 3.927 | 2.930 | 0.292 | [0.158, 0.444] | 0.286 |
| minimax: semantic mean p, kev-4b-ft-s17 | 28 | 28 | 0.042 | 0.091 | 0.849 | [0.770, 0.932] | 0.929 |
| minimax: confirmed rate, kev-4b-ft-s18 | 28 | 28 | 3.906 | 2.952 | 0.298 | [0.162, 0.457] | 0.321 |
| minimax: semantic mean p, kev-4b-ft-s18 | 28 | 28 | 0.034 | 0.081 | 0.838 | [0.737, 0.925] | 0.857 |
| minimax: confirmed rate, kev-4b-ft-s19 | 28 | 28 | 3.854 | 2.851 | 0.276 | [0.157, 0.412] | 0.357 |
| minimax: semantic mean p, kev-4b-ft-s19 | 28 | 28 | 0.043 | 0.081 | 0.779 | [0.670, 0.878] | 0.821 |
| minimax: confirmed rate, kev-9b | 28 | 28 | 2.975 | 2.412 | 0.351 | [0.210, 0.506] | 0.286 |
| minimax: semantic mean p, kev-9b | 28 | 28 | 0.255 | 0.286 | 0.556 | [0.404, 0.700] | 0.536 |
| minimax: confirmed rate, kev-9b-ft-s17 | 28 | 28 | 4.036 | 3.091 | 0.302 | [0.170, 0.459] | 0.357 |
| minimax: semantic mean p, kev-9b-ft-s17 | 28 | 28 | 0.021 | 0.051 | 0.884 | [0.801, 0.963] | 0.964 |
| minimax: confirmed rate, kev-9b-ft-s18 | 28 | 28 | 3.993 | 3.212 | 0.341 | [0.195, 0.506] | 0.357 |
| minimax: semantic mean p, kev-9b-ft-s18 | 28 | 28 | 0.023 | 0.053 | 0.886 | [0.796, 0.966] | 0.929 |
| minimax: confirmed rate, kev-9b-ft-s19 | 28 | 28 | 3.919 | 3.080 | 0.312 | [0.172, 0.469] | 0.321 |
| minimax: semantic mean p, kev-9b-ft-s19 | 28 | 28 | 0.024 | 0.055 | 0.885 | [0.798, 0.960] | 0.893 |
| minimax: confirmed rate, laya-english | 28 | 28 | 0.498 | 0.632 | 0.594 | [0.417, 0.764] | 0.571 |
| minimax: semantic mean p, laya-english | 28 | 28 | 0.392 | 0.585 | 0.923 | [0.848, 0.980] | 0.929 |
| minimax: confirmed rate, laya-multilingual | 28 | 28 | 0.452 | 0.247 | 0.522 | [0.370, 0.674] | 0.429 |
| minimax: semantic mean p, laya-multilingual | 28 | 28 | 0.576 | 0.755 | 0.713 | [0.596, 0.827] | 0.821 |
| minimax: confirmed rate, laya-typed-decisions | 28 | 28 | 0.382 | 0.026 | 0.397 | [0.287, 0.498] | 0.375 |
| minimax: semantic mean p, laya-typed-decisions | 28 | 28 | 0.408 | 0.507 | 0.767 | [0.643, 0.878] | 0.821 |
| minimax: confirmed rate, v3-kev-0.8b-ft-s17 | 28 | 28 | 3.790 | 2.682 | 0.293 | [0.159, 0.441] | 0.250 |
| minimax: semantic mean p, v3-kev-0.8b-ft-s17 | 28 | 28 | 0.087 | 0.110 | 0.638 | [0.506, 0.760] | 0.607 |
| minimax: confirmed rate, v3-kev-0.8b-ft-s18 | 28 | 28 | 3.660 | 2.922 | 0.371 | [0.236, 0.504] | 0.286 |
| minimax: semantic mean p, v3-kev-0.8b-ft-s18 | 28 | 28 | 0.061 | 0.067 | 0.528 | [0.407, 0.651] | 0.464 |
| minimax: confirmed rate, v3-kev-0.8b-ft-s19 | 28 | 28 | 3.937 | 2.950 | 0.334 | [0.210, 0.459] | 0.214 |
| minimax: semantic mean p, v3-kev-0.8b-ft-s19 | 28 | 28 | 0.056 | 0.059 | 0.514 | [0.375, 0.649] | 0.393 |
| minimax: confirmed rate, v3-kev-4b-ft-s17 | 28 | 28 | 3.866 | 3.146 | 0.360 | [0.222, 0.510] | 0.357 |
| minimax: semantic mean p, v3-kev-4b-ft-s17 | 28 | 28 | 0.032 | 0.054 | 0.802 | [0.685, 0.901] | 0.821 |
| minimax: confirmed rate, v3-kev-4b-ft-s18 | 28 | 28 | 3.773 | 3.228 | 0.406 | [0.261, 0.551] | 0.393 |
| minimax: semantic mean p, v3-kev-4b-ft-s18 | 28 | 28 | 0.036 | 0.058 | 0.804 | [0.691, 0.898] | 0.821 |
| minimax: confirmed rate, v3-kev-4b-ft-s19 | 28 | 28 | 4.154 | 3.249 | 0.333 | [0.198, 0.486] | 0.321 |
| minimax: semantic mean p, v3-kev-4b-ft-s19 | 28 | 28 | 0.027 | 0.039 | 0.731 | [0.612, 0.841] | 0.750 |
| minimax: confirmed rate, v3-kev-9b-ft-s17 | 28 | 28 | 3.970 | 3.317 | 0.358 | [0.218, 0.505] | 0.393 |
| minimax: semantic mean p, v3-kev-9b-ft-s17 | 28 | 28 | 0.036 | 0.067 | 0.853 | [0.759, 0.934] | 0.929 |
| minimax: confirmed rate, v3-kev-9b-ft-s18 | 28 | 28 | 3.857 | 3.347 | 0.393 | [0.254, 0.538] | 0.357 |
| minimax: semantic mean p, v3-kev-9b-ft-s18 | 28 | 28 | 0.051 | 0.073 | 0.732 | [0.594, 0.844] | 0.750 |
| minimax: confirmed rate, v3-kev-9b-ft-s19 | 28 | 28 | 4.113 | 3.443 | 0.392 | [0.251, 0.537] | 0.393 |
| minimax: semantic mean p, v3-kev-9b-ft-s19 | 28 | 28 | 0.035 | 0.050 | 0.723 | [0.592, 0.843] | 0.821 |
| mistral: lint rate | 42 | 42 | 6.472 | 6.227 | 0.442 | [0.323, 0.569] | 0.500 |
| mistral: confirmed rate, kev-0.8b | 42 | 42 | 0.037 | 0.023 | 0.468 | [0.395, 0.545] | 0.476 |
| mistral: semantic mean p, kev-0.8b | 42 | 42 | 0.239 | 0.229 | 0.229 | [0.126, 0.347] | 0.167 |
| mistral: confirmed rate, kev-0.8b-ft-s17 | 42 | 42 | 3.783 | 3.793 | 0.520 | [0.404, 0.641] | 0.571 |
| mistral: semantic mean p, kev-0.8b-ft-s17 | 42 | 42 | 0.059 | 0.079 | 0.653 | [0.557, 0.749] | 0.738 |
| mistral: confirmed rate, kev-0.8b-ft-s18 | 42 | 42 | 3.686 | 3.670 | 0.521 | [0.410, 0.636] | 0.595 |
| mistral: semantic mean p, kev-0.8b-ft-s18 | 42 | 42 | 0.067 | 0.080 | 0.579 | [0.491, 0.666] | 0.619 |
| mistral: confirmed rate, kev-0.8b-ft-s19 | 42 | 42 | 3.723 | 3.593 | 0.503 | [0.397, 0.614] | 0.524 |
| mistral: semantic mean p, kev-0.8b-ft-s19 | 42 | 42 | 0.057 | 0.072 | 0.614 | [0.515, 0.710] | 0.643 |
| mistral: confirmed rate, kev-4b | 42 | 42 | 0.480 | 0.459 | 0.541 | [0.439, 0.638] | 0.512 |
| mistral: semantic mean p, kev-4b | 42 | 42 | 0.253 | 0.276 | 0.561 | [0.458, 0.659] | 0.619 |
| mistral: confirmed rate, kev-4b-ft-s17 | 42 | 42 | 4.037 | 3.956 | 0.497 | [0.384, 0.614] | 0.548 |
| mistral: semantic mean p, kev-4b-ft-s17 | 42 | 42 | 0.046 | 0.067 | 0.785 | [0.684, 0.880] | 0.833 |
| mistral: confirmed rate, kev-4b-ft-s18 | 42 | 42 | 3.989 | 3.978 | 0.503 | [0.386, 0.617] | 0.524 |
| mistral: semantic mean p, kev-4b-ft-s18 | 42 | 42 | 0.039 | 0.053 | 0.717 | [0.614, 0.820] | 0.833 |
| mistral: confirmed rate, kev-4b-ft-s19 | 42 | 42 | 3.984 | 3.665 | 0.460 | [0.346, 0.578] | 0.500 |
| mistral: semantic mean p, kev-4b-ft-s19 | 42 | 42 | 0.045 | 0.061 | 0.703 | [0.591, 0.811] | 0.762 |
| mistral: confirmed rate, kev-9b | 42 | 42 | 3.169 | 2.800 | 0.436 | [0.328, 0.544] | 0.333 |
| mistral: semantic mean p, kev-9b | 42 | 42 | 0.266 | 0.283 | 0.470 | [0.363, 0.581] | 0.524 |
| mistral: confirmed rate, kev-9b-ft-s17 | 42 | 42 | 4.155 | 4.020 | 0.505 | [0.388, 0.624] | 0.548 |
| mistral: semantic mean p, kev-9b-ft-s17 | 42 | 42 | 0.024 | 0.036 | 0.730 | [0.624, 0.827] | 0.738 |
| mistral: confirmed rate, kev-9b-ft-s18 | 42 | 42 | 4.098 | 4.123 | 0.523 | [0.409, 0.641] | 0.571 |
| mistral: semantic mean p, kev-9b-ft-s18 | 42 | 42 | 0.025 | 0.040 | 0.795 | [0.690, 0.891] | 0.786 |
| mistral: confirmed rate, kev-9b-ft-s19 | 42 | 42 | 4.071 | 4.164 | 0.527 | [0.422, 0.639] | 0.595 |
| mistral: semantic mean p, kev-9b-ft-s19 | 42 | 42 | 0.027 | 0.040 | 0.739 | [0.633, 0.842] | 0.762 |
| mistral: confirmed rate, laya-english | 42 | 42 | 0.762 | 0.917 | 0.522 | [0.407, 0.635] | 0.583 |
| mistral: semantic mean p, laya-english | 42 | 42 | 0.420 | 0.591 | 0.864 | [0.785, 0.934] | 0.857 |
| mistral: confirmed rate, laya-multilingual | 42 | 42 | 0.445 | 0.324 | 0.448 | [0.346, 0.552] | 0.429 |
| mistral: semantic mean p, laya-multilingual | 42 | 42 | 0.615 | 0.729 | 0.634 | [0.519, 0.742] | 0.643 |
| mistral: confirmed rate, laya-typed-decisions | 42 | 42 | 0.708 | 0.362 | 0.487 | [0.401, 0.571] | 0.452 |
| mistral: semantic mean p, laya-typed-decisions | 42 | 42 | 0.438 | 0.518 | 0.717 | [0.628, 0.810] | 0.762 |
| mistral: confirmed rate, v3-kev-0.8b-ft-s17 | 42 | 42 | 3.865 | 3.662 | 0.493 | [0.389, 0.604] | 0.571 |
| mistral: semantic mean p, v3-kev-0.8b-ft-s17 | 42 | 42 | 0.094 | 0.102 | 0.518 | [0.408, 0.628] | 0.476 |
| mistral: confirmed rate, v3-kev-0.8b-ft-s18 | 42 | 42 | 3.735 | 3.459 | 0.477 | [0.369, 0.589] | 0.548 |
| mistral: semantic mean p, v3-kev-0.8b-ft-s18 | 42 | 42 | 0.068 | 0.070 | 0.482 | [0.381, 0.583] | 0.476 |
| mistral: confirmed rate, v3-kev-0.8b-ft-s19 | 42 | 42 | 4.068 | 3.689 | 0.460 | [0.353, 0.570] | 0.500 |
| mistral: semantic mean p, v3-kev-0.8b-ft-s19 | 42 | 42 | 0.062 | 0.060 | 0.460 | [0.352, 0.572] | 0.524 |
| mistral: confirmed rate, v3-kev-4b-ft-s17 | 42 | 42 | 4.047 | 3.880 | 0.490 | [0.371, 0.609] | 0.548 |
| mistral: semantic mean p, v3-kev-4b-ft-s17 | 42 | 42 | 0.036 | 0.048 | 0.675 | [0.575, 0.776] | 0.738 |
| mistral: confirmed rate, v3-kev-4b-ft-s18 | 42 | 42 | 3.925 | 3.958 | 0.508 | [0.394, 0.628] | 0.595 |
| mistral: semantic mean p, v3-kev-4b-ft-s18 | 42 | 42 | 0.041 | 0.051 | 0.662 | [0.557, 0.764] | 0.738 |
| mistral: confirmed rate, v3-kev-4b-ft-s19 | 42 | 42 | 4.295 | 4.181 | 0.499 | [0.387, 0.618] | 0.595 |
| mistral: semantic mean p, v3-kev-4b-ft-s19 | 42 | 42 | 0.029 | 0.037 | 0.653 | [0.554, 0.753] | 0.714 |
| mistral: confirmed rate, v3-kev-9b-ft-s17 | 42 | 42 | 4.173 | 4.236 | 0.523 | [0.414, 0.644] | 0.643 |
| mistral: semantic mean p, v3-kev-9b-ft-s17 | 42 | 42 | 0.041 | 0.053 | 0.659 | [0.553, 0.755] | 0.643 |
| mistral: confirmed rate, v3-kev-9b-ft-s18 | 42 | 42 | 4.054 | 4.151 | 0.532 | [0.416, 0.651] | 0.643 |
| mistral: semantic mean p, v3-kev-9b-ft-s18 | 42 | 42 | 0.056 | 0.062 | 0.604 | [0.484, 0.715] | 0.595 |
| mistral: confirmed rate, v3-kev-9b-ft-s19 | 42 | 42 | 4.282 | 4.264 | 0.518 | [0.409, 0.636] | 0.619 |
| mistral: semantic mean p, v3-kev-9b-ft-s19 | 42 | 42 | 0.038 | 0.043 | 0.577 | [0.462, 0.687] | 0.619 |
| moonshot: lint rate | 15 | 15 | 6.157 | 8.114 | 0.787 | [0.622, 0.938] | 0.867 |
| moonshot: confirmed rate, kev-0.8b | 15 | 15 | 0.133 | 0.249 | 0.571 | [0.444, 0.700] | 0.533 |
| moonshot: semantic mean p, kev-0.8b | 15 | 15 | 0.250 | 0.238 | 0.253 | [0.089, 0.427] | 0.267 |
| moonshot: confirmed rate, kev-0.8b-ft-s17 | 15 | 15 | 3.500 | 5.202 | 0.778 | [0.582, 0.951] | 0.800 |
| moonshot: semantic mean p, kev-0.8b-ft-s17 | 15 | 15 | 0.067 | 0.072 | 0.524 | [0.307, 0.711] | 0.467 |
| moonshot: confirmed rate, kev-0.8b-ft-s18 | 15 | 15 | 3.492 | 4.814 | 0.729 | [0.533, 0.907] | 0.800 |
| moonshot: semantic mean p, kev-0.8b-ft-s18 | 15 | 15 | 0.069 | 0.078 | 0.600 | [0.404, 0.796] | 0.667 |
| moonshot: confirmed rate, kev-0.8b-ft-s19 | 15 | 15 | 3.324 | 4.761 | 0.711 | [0.511, 0.898] | 0.733 |
| moonshot: semantic mean p, kev-0.8b-ft-s19 | 15 | 15 | 0.065 | 0.071 | 0.587 | [0.396, 0.778] | 0.600 |
| moonshot: confirmed rate, kev-4b | 15 | 15 | 0.755 | 0.630 | 0.433 | [0.238, 0.633] | 0.400 |
| moonshot: semantic mean p, kev-4b | 15 | 15 | 0.269 | 0.277 | 0.404 | [0.191, 0.627] | 0.333 |
| moonshot: confirmed rate, kev-4b-ft-s17 | 15 | 15 | 3.506 | 5.699 | 0.822 | [0.662, 0.973] | 0.867 |
| moonshot: semantic mean p, kev-4b-ft-s17 | 15 | 15 | 0.045 | 0.063 | 0.751 | [0.573, 0.907] | 0.800 |
| moonshot: confirmed rate, kev-4b-ft-s18 | 15 | 15 | 3.466 | 5.656 | 0.858 | [0.720, 0.978] | 0.933 |
| moonshot: semantic mean p, kev-4b-ft-s18 | 15 | 15 | 0.037 | 0.051 | 0.742 | [0.547, 0.907] | 0.733 |
| moonshot: confirmed rate, kev-4b-ft-s19 | 15 | 15 | 3.692 | 5.436 | 0.787 | [0.627, 0.938] | 0.867 |
| moonshot: semantic mean p, kev-4b-ft-s19 | 15 | 15 | 0.040 | 0.052 | 0.738 | [0.542, 0.898] | 0.733 |
| moonshot: confirmed rate, kev-9b | 15 | 15 | 2.788 | 4.320 | 0.769 | [0.631, 0.907] | 0.800 |
| moonshot: semantic mean p, kev-9b | 15 | 15 | 0.264 | 0.276 | 0.453 | [0.302, 0.604] | 0.533 |
| moonshot: confirmed rate, kev-9b-ft-s17 | 15 | 15 | 3.285 | 5.768 | 0.867 | [0.733, 0.987] | 0.933 |
| moonshot: semantic mean p, kev-9b-ft-s17 | 15 | 15 | 0.024 | 0.037 | 0.698 | [0.524, 0.871] | 0.733 |
| moonshot: confirmed rate, kev-9b-ft-s18 | 15 | 15 | 3.317 | 5.728 | 0.884 | [0.742, 1.000] | 0.933 |
| moonshot: semantic mean p, kev-9b-ft-s18 | 15 | 15 | 0.024 | 0.035 | 0.724 | [0.529, 0.924] | 0.667 |
| moonshot: confirmed rate, kev-9b-ft-s19 | 15 | 15 | 3.444 | 5.810 | 0.804 | [0.662, 0.947] | 0.867 |
| moonshot: semantic mean p, kev-9b-ft-s19 | 15 | 15 | 0.024 | 0.037 | 0.760 | [0.587, 0.911] | 0.733 |
| moonshot: confirmed rate, laya-english | 15 | 15 | 0.908 | 1.976 | 0.738 | [0.651, 0.876] | 0.967 |
| moonshot: semantic mean p, laya-english | 15 | 15 | 0.424 | 0.547 | 0.769 | [0.582, 0.916] | 0.733 |
| moonshot: confirmed rate, laya-multilingual | 15 | 15 | 0.458 | 0.183 | 0.391 | [0.204, 0.576] | 0.367 |
| moonshot: semantic mean p, laya-multilingual | 15 | 15 | 0.627 | 0.797 | 0.729 | [0.551, 0.867] | 0.667 |
| moonshot: confirmed rate, laya-typed-decisions | 15 | 15 | 0.708 | 0.318 | 0.422 | [0.300, 0.538] | 0.433 |
| moonshot: semantic mean p, laya-typed-decisions | 15 | 15 | 0.460 | 0.494 | 0.582 | [0.373, 0.773] | 0.533 |
| moonshot: confirmed rate, v3-kev-0.8b-ft-s17 | 15 | 15 | 3.319 | 5.208 | 0.804 | [0.631, 0.951] | 0.800 |
| moonshot: semantic mean p, v3-kev-0.8b-ft-s17 | 15 | 15 | 0.111 | 0.100 | 0.436 | [0.236, 0.627] | 0.400 |
| moonshot: confirmed rate, v3-kev-0.8b-ft-s18 | 15 | 15 | 3.427 | 4.955 | 0.742 | [0.551, 0.916] | 0.733 |
| moonshot: semantic mean p, v3-kev-0.8b-ft-s18 | 15 | 15 | 0.077 | 0.071 | 0.453 | [0.267, 0.644] | 0.333 |
| moonshot: confirmed rate, v3-kev-0.8b-ft-s19 | 15 | 15 | 4.138 | 5.315 | 0.716 | [0.560, 0.889] | 0.800 |
| moonshot: semantic mean p, v3-kev-0.8b-ft-s19 | 15 | 15 | 0.071 | 0.060 | 0.396 | [0.182, 0.604] | 0.267 |
| moonshot: confirmed rate, v3-kev-4b-ft-s17 | 15 | 15 | 3.621 | 5.293 | 0.787 | [0.627, 0.933] | 0.800 |
| moonshot: semantic mean p, v3-kev-4b-ft-s17 | 15 | 15 | 0.035 | 0.046 | 0.693 | [0.538, 0.853] | 0.800 |
| moonshot: confirmed rate, v3-kev-4b-ft-s18 | 15 | 15 | 3.688 | 5.539 | 0.747 | [0.560, 0.911] | 0.733 |
| moonshot: semantic mean p, v3-kev-4b-ft-s18 | 15 | 15 | 0.038 | 0.051 | 0.720 | [0.547, 0.893] | 0.800 |
| moonshot: confirmed rate, v3-kev-4b-ft-s19 | 15 | 15 | 3.971 | 6.115 | 0.858 | [0.707, 0.996] | 0.867 |
| moonshot: semantic mean p, v3-kev-4b-ft-s19 | 15 | 15 | 0.030 | 0.036 | 0.671 | [0.502, 0.831] | 0.733 |
| moonshot: confirmed rate, v3-kev-9b-ft-s17 | 15 | 15 | 3.464 | 5.835 | 0.898 | [0.756, 1.000] | 0.933 |
| moonshot: semantic mean p, v3-kev-9b-ft-s17 | 15 | 15 | 0.046 | 0.055 | 0.747 | [0.538, 0.920] | 0.733 |
| moonshot: confirmed rate, v3-kev-9b-ft-s18 | 15 | 15 | 3.320 | 5.700 | 0.862 | [0.711, 0.991] | 0.867 |
| moonshot: semantic mean p, v3-kev-9b-ft-s18 | 15 | 15 | 0.059 | 0.070 | 0.756 | [0.551, 0.933] | 0.733 |
| moonshot: confirmed rate, v3-kev-9b-ft-s19 | 15 | 15 | 3.473 | 6.060 | 0.880 | [0.738, 1.000] | 0.933 |
| moonshot: semantic mean p, v3-kev-9b-ft-s19 | 15 | 15 | 0.040 | 0.048 | 0.720 | [0.498, 0.920] | 0.733 |
| nvidia: lint rate | 28 | 28 | 6.382 | 6.297 | 0.473 | [0.311, 0.642] | 0.536 |
| nvidia: confirmed rate, kev-0.8b | 28 | 28 | 0.068 | 0.146 | 0.462 | [0.358, 0.562] | 0.464 |
| nvidia: semantic mean p, kev-0.8b | 28 | 28 | 0.240 | 0.237 | 0.265 | [0.143, 0.406] | 0.214 |
| nvidia: confirmed rate, kev-0.8b-ft-s17 | 28 | 28 | 3.914 | 3.886 | 0.463 | [0.311, 0.633] | 0.571 |
| nvidia: semantic mean p, kev-0.8b-ft-s17 | 28 | 28 | 0.059 | 0.077 | 0.691 | [0.562, 0.818] | 0.750 |
| nvidia: confirmed rate, kev-0.8b-ft-s18 | 28 | 28 | 3.718 | 3.570 | 0.453 | [0.306, 0.617] | 0.607 |
| nvidia: semantic mean p, kev-0.8b-ft-s18 | 28 | 28 | 0.064 | 0.085 | 0.673 | [0.555, 0.782] | 0.714 |
| nvidia: confirmed rate, kev-0.8b-ft-s19 | 28 | 28 | 3.625 | 3.475 | 0.459 | [0.311, 0.625] | 0.571 |
| nvidia: semantic mean p, kev-0.8b-ft-s19 | 28 | 28 | 0.054 | 0.081 | 0.737 | [0.599, 0.860] | 0.750 |
| nvidia: confirmed rate, kev-4b | 28 | 28 | 0.557 | 0.474 | 0.453 | [0.309, 0.603] | 0.482 |
| nvidia: semantic mean p, kev-4b | 28 | 28 | 0.246 | 0.274 | 0.520 | [0.392, 0.651] | 0.536 |
| nvidia: confirmed rate, kev-4b-ft-s17 | 28 | 28 | 3.860 | 4.197 | 0.514 | [0.367, 0.676] | 0.607 |
| nvidia: semantic mean p, kev-4b-ft-s17 | 28 | 28 | 0.037 | 0.070 | 0.869 | [0.772, 0.948] | 0.893 |
| nvidia: confirmed rate, kev-4b-ft-s18 | 28 | 28 | 3.813 | 4.171 | 0.515 | [0.367, 0.682] | 0.607 |
| nvidia: semantic mean p, kev-4b-ft-s18 | 28 | 28 | 0.030 | 0.057 | 0.846 | [0.744, 0.929] | 0.821 |
| nvidia: confirmed rate, kev-4b-ft-s19 | 28 | 28 | 3.854 | 4.114 | 0.508 | [0.360, 0.672] | 0.607 |
| nvidia: semantic mean p, kev-4b-ft-s19 | 28 | 28 | 0.035 | 0.066 | 0.874 | [0.773, 0.955] | 0.857 |
| nvidia: confirmed rate, kev-9b | 28 | 28 | 3.455 | 3.248 | 0.454 | [0.290, 0.640] | 0.500 |
| nvidia: semantic mean p, kev-9b | 28 | 28 | 0.254 | 0.279 | 0.483 | [0.328, 0.643] | 0.500 |
| nvidia: confirmed rate, kev-9b-ft-s17 | 28 | 28 | 3.934 | 4.244 | 0.524 | [0.367, 0.698] | 0.607 |
| nvidia: semantic mean p, kev-9b-ft-s17 | 28 | 28 | 0.020 | 0.043 | 0.793 | [0.684, 0.888] | 0.786 |
| nvidia: confirmed rate, kev-9b-ft-s18 | 28 | 28 | 4.004 | 4.386 | 0.542 | [0.385, 0.714] | 0.607 |
| nvidia: semantic mean p, kev-9b-ft-s18 | 28 | 28 | 0.019 | 0.049 | 0.886 | [0.818, 0.957] | 1.000 |
| nvidia: confirmed rate, kev-9b-ft-s19 | 28 | 28 | 4.061 | 4.288 | 0.518 | [0.360, 0.693] | 0.607 |
| nvidia: semantic mean p, kev-9b-ft-s19 | 28 | 28 | 0.020 | 0.044 | 0.838 | [0.750, 0.920] | 0.893 |
| nvidia: confirmed rate, laya-english | 28 | 28 | 1.096 | 1.065 | 0.518 | [0.384, 0.647] | 0.446 |
| nvidia: semantic mean p, laya-english | 28 | 28 | 0.379 | 0.506 | 0.708 | [0.582, 0.827] | 0.714 |
| nvidia: confirmed rate, laya-multilingual | 28 | 28 | 0.463 | 0.319 | 0.436 | [0.313, 0.562] | 0.464 |
| nvidia: semantic mean p, laya-multilingual | 28 | 28 | 0.585 | 0.672 | 0.570 | [0.455, 0.695] | 0.571 |
| nvidia: confirmed rate, laya-typed-decisions | 28 | 28 | 1.002 | 0.389 | 0.430 | [0.330, 0.527] | 0.393 |
| nvidia: semantic mean p, laya-typed-decisions | 28 | 28 | 0.396 | 0.493 | 0.694 | [0.583, 0.811] | 0.750 |
| nvidia: confirmed rate, v3-kev-0.8b-ft-s17 | 28 | 28 | 3.791 | 3.501 | 0.440 | [0.295, 0.607] | 0.571 |
| nvidia: semantic mean p, v3-kev-0.8b-ft-s17 | 28 | 28 | 0.101 | 0.117 | 0.611 | [0.510, 0.713] | 0.679 |
| nvidia: confirmed rate, v3-kev-0.8b-ft-s18 | 28 | 28 | 3.772 | 3.570 | 0.458 | [0.306, 0.628] | 0.607 |
| nvidia: semantic mean p, v3-kev-0.8b-ft-s18 | 28 | 28 | 0.069 | 0.079 | 0.596 | [0.483, 0.707] | 0.571 |
| nvidia: confirmed rate, v3-kev-0.8b-ft-s19 | 28 | 28 | 4.023 | 3.760 | 0.443 | [0.297, 0.606] | 0.571 |
| nvidia: semantic mean p, v3-kev-0.8b-ft-s19 | 28 | 28 | 0.065 | 0.072 | 0.580 | [0.478, 0.691] | 0.643 |
| nvidia: confirmed rate, v3-kev-4b-ft-s17 | 28 | 28 | 3.936 | 4.192 | 0.508 | [0.357, 0.679] | 0.571 |
| nvidia: semantic mean p, v3-kev-4b-ft-s17 | 28 | 28 | 0.032 | 0.054 | 0.791 | [0.657, 0.895] | 0.786 |
| nvidia: confirmed rate, v3-kev-4b-ft-s18 | 28 | 28 | 3.933 | 4.246 | 0.522 | [0.374, 0.688] | 0.571 |
| nvidia: semantic mean p, v3-kev-4b-ft-s18 | 28 | 28 | 0.034 | 0.056 | 0.790 | [0.677, 0.886] | 0.750 |
| nvidia: confirmed rate, v3-kev-4b-ft-s19 | 28 | 28 | 4.092 | 4.222 | 0.500 | [0.346, 0.671] | 0.571 |
| nvidia: semantic mean p, v3-kev-4b-ft-s19 | 28 | 28 | 0.023 | 0.040 | 0.805 | [0.695, 0.902] | 0.821 |
| nvidia: confirmed rate, v3-kev-9b-ft-s17 | 28 | 28 | 4.082 | 4.416 | 0.526 | [0.374, 0.700] | 0.607 |
| nvidia: semantic mean p, v3-kev-9b-ft-s17 | 28 | 28 | 0.035 | 0.063 | 0.798 | [0.694, 0.894] | 0.857 |
| nvidia: confirmed rate, v3-kev-9b-ft-s18 | 28 | 28 | 4.006 | 4.272 | 0.522 | [0.365, 0.696] | 0.607 |
| nvidia: semantic mean p, v3-kev-9b-ft-s18 | 28 | 28 | 0.049 | 0.074 | 0.732 | [0.612, 0.839] | 0.750 |
| nvidia: confirmed rate, v3-kev-9b-ft-s19 | 28 | 28 | 4.138 | 4.428 | 0.526 | [0.369, 0.702] | 0.607 |
| nvidia: semantic mean p, v3-kev-9b-ft-s19 | 28 | 28 | 0.032 | 0.053 | 0.786 | [0.681, 0.881] | 0.786 |
| openai: lint rate | 58 | 58 | 6.331 | 5.546 | 0.405 | [0.305, 0.507] | 0.362 |
| openai: confirmed rate, kev-0.8b | 58 | 58 | 0.064 | 0.023 | 0.485 | [0.422, 0.555] | 0.466 |
| openai: semantic mean p, kev-0.8b | 58 | 58 | 0.224 | 0.249 | 0.430 | [0.332, 0.523] | 0.293 |
| openai: confirmed rate, kev-0.8b-ft-s17 | 58 | 58 | 3.561 | 3.336 | 0.475 | [0.374, 0.574] | 0.448 |
| openai: semantic mean p, kev-0.8b-ft-s17 | 58 | 58 | 0.062 | 0.086 | 0.719 | [0.627, 0.809] | 0.707 |
| openai: confirmed rate, kev-0.8b-ft-s18 | 58 | 58 | 3.442 | 3.044 | 0.446 | [0.342, 0.545] | 0.397 |
| openai: semantic mean p, kev-0.8b-ft-s18 | 58 | 58 | 0.068 | 0.090 | 0.688 | [0.607, 0.769] | 0.724 |
| openai: confirmed rate, kev-0.8b-ft-s19 | 58 | 58 | 3.380 | 3.091 | 0.458 | [0.350, 0.559] | 0.431 |
| openai: semantic mean p, kev-0.8b-ft-s19 | 58 | 58 | 0.055 | 0.082 | 0.732 | [0.642, 0.815] | 0.707 |
| openai: confirmed rate, kev-4b | 58 | 58 | 0.465 | 0.348 | 0.444 | [0.345, 0.540] | 0.388 |
| openai: semantic mean p, kev-4b | 58 | 58 | 0.228 | 0.280 | 0.674 | [0.585, 0.762] | 0.690 |
| openai: confirmed rate, kev-4b-ft-s17 | 58 | 58 | 3.697 | 3.487 | 0.477 | [0.367, 0.581] | 0.431 |
| openai: semantic mean p, kev-4b-ft-s17 | 58 | 58 | 0.040 | 0.085 | 0.889 | [0.819, 0.950] | 0.879 |
| openai: confirmed rate, kev-4b-ft-s18 | 58 | 58 | 3.649 | 3.477 | 0.478 | [0.366, 0.585] | 0.397 |
| openai: semantic mean p, kev-4b-ft-s18 | 58 | 58 | 0.034 | 0.072 | 0.847 | [0.770, 0.913] | 0.845 |
| openai: confirmed rate, kev-4b-ft-s19 | 58 | 58 | 3.662 | 3.351 | 0.457 | [0.346, 0.564] | 0.397 |
| openai: semantic mean p, kev-4b-ft-s19 | 58 | 58 | 0.039 | 0.079 | 0.851 | [0.776, 0.916] | 0.897 |
| openai: confirmed rate, kev-9b | 58 | 58 | 3.030 | 2.683 | 0.452 | [0.351, 0.554] | 0.414 |
| openai: semantic mean p, kev-9b | 58 | 58 | 0.240 | 0.279 | 0.515 | [0.407, 0.627] | 0.517 |
| openai: confirmed rate, kev-9b-ft-s17 | 58 | 58 | 3.669 | 3.405 | 0.474 | [0.368, 0.575] | 0.448 |
| openai: semantic mean p, kev-9b-ft-s17 | 58 | 58 | 0.022 | 0.049 | 0.838 | [0.762, 0.906] | 0.845 |
| openai: confirmed rate, kev-9b-ft-s18 | 58 | 58 | 3.710 | 3.594 | 0.493 | [0.381, 0.596] | 0.414 |
| openai: semantic mean p, kev-9b-ft-s18 | 58 | 58 | 0.022 | 0.050 | 0.854 | [0.786, 0.915] | 0.879 |
| openai: confirmed rate, kev-9b-ft-s19 | 58 | 58 | 3.769 | 3.502 | 0.464 | [0.360, 0.565] | 0.431 |
| openai: semantic mean p, kev-9b-ft-s19 | 58 | 58 | 0.022 | 0.046 | 0.853 | [0.782, 0.916] | 0.862 |
| openai: confirmed rate, laya-english | 58 | 58 | 1.019 | 0.911 | 0.515 | [0.433, 0.603] | 0.621 |
| openai: semantic mean p, laya-english | 58 | 58 | 0.370 | 0.504 | 0.704 | [0.616, 0.795] | 0.707 |
| openai: confirmed rate, laya-multilingual | 58 | 58 | 0.414 | 0.333 | 0.467 | [0.366, 0.566] | 0.440 |
| openai: semantic mean p, laya-multilingual | 58 | 58 | 0.523 | 0.683 | 0.660 | [0.558, 0.763] | 0.655 |
| openai: confirmed rate, laya-typed-decisions | 58 | 58 | 0.818 | 0.158 | 0.381 | [0.320, 0.439] | 0.336 |
| openai: semantic mean p, laya-typed-decisions | 58 | 58 | 0.376 | 0.472 | 0.689 | [0.598, 0.780] | 0.655 |
| openai: confirmed rate, v3-kev-0.8b-ft-s17 | 58 | 58 | 3.527 | 3.067 | 0.435 | [0.334, 0.532] | 0.414 |
| openai: semantic mean p, v3-kev-0.8b-ft-s17 | 58 | 58 | 0.102 | 0.120 | 0.614 | [0.521, 0.705] | 0.603 |
| openai: confirmed rate, v3-kev-0.8b-ft-s18 | 58 | 58 | 3.556 | 3.077 | 0.438 | [0.334, 0.538] | 0.414 |
| openai: semantic mean p, v3-kev-0.8b-ft-s18 | 58 | 58 | 0.071 | 0.079 | 0.574 | [0.478, 0.667] | 0.638 |
| openai: confirmed rate, v3-kev-0.8b-ft-s19 | 58 | 58 | 3.782 | 3.375 | 0.441 | [0.337, 0.536] | 0.431 |
| openai: semantic mean p, v3-kev-0.8b-ft-s19 | 58 | 58 | 0.066 | 0.076 | 0.584 | [0.493, 0.679] | 0.603 |
| openai: confirmed rate, v3-kev-4b-ft-s17 | 58 | 58 | 3.683 | 3.346 | 0.443 | [0.331, 0.550] | 0.362 |
| openai: semantic mean p, v3-kev-4b-ft-s17 | 58 | 58 | 0.033 | 0.057 | 0.771 | [0.685, 0.853] | 0.828 |
| openai: confirmed rate, v3-kev-4b-ft-s18 | 58 | 58 | 3.752 | 3.556 | 0.469 | [0.363, 0.570] | 0.379 |
| openai: semantic mean p, v3-kev-4b-ft-s18 | 58 | 58 | 0.036 | 0.060 | 0.769 | [0.676, 0.854] | 0.793 |
| openai: confirmed rate, v3-kev-4b-ft-s19 | 58 | 58 | 3.884 | 3.631 | 0.467 | [0.356, 0.572] | 0.431 |
| openai: semantic mean p, v3-kev-4b-ft-s19 | 58 | 58 | 0.026 | 0.043 | 0.762 | [0.674, 0.848] | 0.828 |
| openai: confirmed rate, v3-kev-9b-ft-s17 | 58 | 58 | 3.782 | 3.555 | 0.479 | [0.374, 0.579] | 0.431 |
| openai: semantic mean p, v3-kev-9b-ft-s17 | 58 | 58 | 0.041 | 0.064 | 0.743 | [0.650, 0.833] | 0.759 |
| openai: confirmed rate, v3-kev-9b-ft-s18 | 58 | 58 | 3.723 | 3.616 | 0.494 | [0.389, 0.597] | 0.466 |
| openai: semantic mean p, v3-kev-9b-ft-s18 | 58 | 58 | 0.055 | 0.077 | 0.694 | [0.595, 0.792] | 0.724 |
| openai: confirmed rate, v3-kev-9b-ft-s19 | 58 | 58 | 3.890 | 3.777 | 0.489 | [0.380, 0.592] | 0.448 |
| openai: semantic mean p, v3-kev-9b-ft-s19 | 58 | 58 | 0.038 | 0.053 | 0.695 | [0.593, 0.792] | 0.724 |
| qwen: lint rate | 29 | 29 | 6.195 | 6.858 | 0.562 | [0.433, 0.696] | 0.621 |
| qwen: confirmed rate, kev-0.8b | 29 | 29 | 0.045 | 0.118 | 0.532 | [0.467, 0.600] | 0.534 |
| qwen: semantic mean p, kev-0.8b | 29 | 29 | 0.244 | 0.243 | 0.426 | [0.288, 0.565] | 0.414 |
| qwen: confirmed rate, kev-0.8b-ft-s17 | 29 | 29 | 3.497 | 4.460 | 0.641 | [0.535, 0.761] | 0.724 |
| qwen: semantic mean p, kev-0.8b-ft-s17 | 29 | 29 | 0.067 | 0.075 | 0.587 | [0.471, 0.709] | 0.655 |
| qwen: confirmed rate, kev-0.8b-ft-s18 | 29 | 29 | 3.283 | 4.163 | 0.582 | [0.457, 0.710] | 0.586 |
| qwen: semantic mean p, kev-0.8b-ft-s18 | 29 | 29 | 0.073 | 0.082 | 0.612 | [0.486, 0.743] | 0.655 |
| qwen: confirmed rate, kev-0.8b-ft-s19 | 29 | 29 | 3.405 | 4.127 | 0.563 | [0.439, 0.693] | 0.621 |
| qwen: semantic mean p, kev-0.8b-ft-s19 | 29 | 29 | 0.065 | 0.078 | 0.630 | [0.517, 0.751] | 0.759 |
| qwen: confirmed rate, kev-4b | 29 | 29 | 0.484 | 0.604 | 0.595 | [0.486, 0.710] | 0.603 |
| qwen: semantic mean p, kev-4b | 29 | 29 | 0.255 | 0.279 | 0.602 | [0.474, 0.729] | 0.552 |
| qwen: confirmed rate, kev-4b-ft-s17 | 29 | 29 | 3.507 | 4.785 | 0.689 | [0.590, 0.798] | 0.724 |
| qwen: semantic mean p, kev-4b-ft-s17 | 29 | 29 | 0.046 | 0.074 | 0.782 | [0.688, 0.874] | 0.862 |
| qwen: confirmed rate, kev-4b-ft-s18 | 29 | 29 | 3.573 | 4.758 | 0.663 | [0.552, 0.778] | 0.724 |
| qwen: semantic mean p, kev-4b-ft-s18 | 29 | 29 | 0.038 | 0.063 | 0.774 | [0.681, 0.870] | 0.828 |
| qwen: confirmed rate, kev-4b-ft-s19 | 29 | 29 | 3.427 | 4.583 | 0.677 | [0.565, 0.793] | 0.724 |
| qwen: semantic mean p, kev-4b-ft-s19 | 29 | 29 | 0.043 | 0.066 | 0.753 | [0.650, 0.847] | 0.828 |
| qwen: confirmed rate, kev-9b | 29 | 29 | 3.461 | 3.858 | 0.543 | [0.434, 0.658] | 0.690 |
| qwen: semantic mean p, kev-9b | 29 | 29 | 0.266 | 0.283 | 0.493 | [0.348, 0.641] | 0.448 |
| qwen: confirmed rate, kev-9b-ft-s17 | 29 | 29 | 3.781 | 4.688 | 0.598 | [0.461, 0.727] | 0.655 |
| qwen: semantic mean p, kev-9b-ft-s17 | 29 | 29 | 0.028 | 0.049 | 0.793 | [0.684, 0.899] | 0.828 |
| qwen: confirmed rate, kev-9b-ft-s18 | 29 | 29 | 3.716 | 4.963 | 0.677 | [0.551, 0.798] | 0.724 |
| qwen: semantic mean p, kev-9b-ft-s18 | 29 | 29 | 0.028 | 0.052 | 0.816 | [0.718, 0.907] | 0.828 |
| qwen: confirmed rate, kev-9b-ft-s19 | 29 | 29 | 3.694 | 4.818 | 0.669 | [0.534, 0.795] | 0.690 |
| qwen: semantic mean p, kev-9b-ft-s19 | 29 | 29 | 0.028 | 0.045 | 0.786 | [0.663, 0.905] | 0.862 |
| qwen: confirmed rate, laya-english | 29 | 29 | 1.149 | 1.507 | 0.573 | [0.457, 0.694] | 0.552 |
| qwen: semantic mean p, laya-english | 29 | 29 | 0.374 | 0.513 | 0.779 | [0.669, 0.875] | 0.759 |
| qwen: confirmed rate, laya-multilingual | 29 | 29 | 0.387 | 0.371 | 0.547 | [0.410, 0.685] | 0.638 |
| qwen: semantic mean p, laya-multilingual | 29 | 29 | 0.596 | 0.642 | 0.520 | [0.356, 0.673] | 0.448 |
| qwen: confirmed rate, laya-typed-decisions | 29 | 29 | 0.935 | 0.783 | 0.430 | [0.339, 0.519] | 0.466 |
| qwen: semantic mean p, laya-typed-decisions | 29 | 29 | 0.428 | 0.501 | 0.671 | [0.553, 0.786] | 0.586 |
| qwen: confirmed rate, v3-kev-0.8b-ft-s17 | 29 | 29 | 3.374 | 4.176 | 0.577 | [0.439, 0.712] | 0.655 |
| qwen: semantic mean p, v3-kev-0.8b-ft-s17 | 29 | 29 | 0.105 | 0.115 | 0.572 | [0.455, 0.684] | 0.621 |
| qwen: confirmed rate, v3-kev-0.8b-ft-s18 | 29 | 29 | 3.379 | 4.191 | 0.575 | [0.452, 0.703] | 0.655 |
| qwen: semantic mean p, v3-kev-0.8b-ft-s18 | 29 | 29 | 0.075 | 0.079 | 0.555 | [0.449, 0.662] | 0.621 |
| qwen: confirmed rate, v3-kev-0.8b-ft-s19 | 29 | 29 | 4.000 | 4.307 | 0.516 | [0.404, 0.640] | 0.483 |
| qwen: semantic mean p, v3-kev-0.8b-ft-s19 | 29 | 29 | 0.070 | 0.072 | 0.549 | [0.441, 0.658] | 0.586 |
| qwen: confirmed rate, v3-kev-4b-ft-s17 | 29 | 29 | 3.512 | 4.655 | 0.683 | [0.570, 0.797] | 0.759 |
| qwen: semantic mean p, v3-kev-4b-ft-s17 | 29 | 29 | 0.030 | 0.065 | 0.876 | [0.819, 0.936] | 1.000 |
| qwen: confirmed rate, v3-kev-4b-ft-s18 | 29 | 29 | 3.597 | 4.841 | 0.679 | [0.568, 0.792] | 0.724 |
| qwen: semantic mean p, v3-kev-4b-ft-s18 | 29 | 29 | 0.036 | 0.069 | 0.811 | [0.711, 0.894] | 0.828 |
| qwen: confirmed rate, v3-kev-4b-ft-s19 | 29 | 29 | 3.749 | 5.019 | 0.671 | [0.562, 0.776] | 0.724 |
| qwen: semantic mean p, v3-kev-4b-ft-s19 | 29 | 29 | 0.023 | 0.049 | 0.842 | [0.760, 0.924] | 0.931 |
| qwen: confirmed rate, v3-kev-9b-ft-s17 | 29 | 29 | 3.729 | 4.888 | 0.677 | [0.541, 0.813] | 0.724 |
| qwen: semantic mean p, v3-kev-9b-ft-s17 | 29 | 29 | 0.042 | 0.069 | 0.828 | [0.728, 0.913] | 0.828 |
| qwen: confirmed rate, v3-kev-9b-ft-s18 | 29 | 29 | 3.748 | 4.782 | 0.639 | [0.523, 0.756] | 0.724 |
| qwen: semantic mean p, v3-kev-9b-ft-s18 | 29 | 29 | 0.055 | 0.081 | 0.819 | [0.723, 0.905] | 0.897 |
| qwen: confirmed rate, v3-kev-9b-ft-s19 | 29 | 29 | 3.816 | 4.953 | 0.647 | [0.515, 0.773] | 0.724 |
| qwen: semantic mean p, v3-kev-9b-ft-s19 | 29 | 29 | 0.036 | 0.062 | 0.825 | [0.735, 0.906] | 0.897 |
| zai: lint rate | 28 | 28 | 6.575 | 6.560 | 0.445 | [0.268, 0.635] | 0.393 |
| zai: confirmed rate, kev-0.8b | 28 | 28 | 0.076 | 0.018 | 0.463 | [0.407, 0.502] | 0.464 |
| zai: semantic mean p, kev-0.8b | 28 | 28 | 0.255 | 0.238 | 0.344 | [0.240, 0.453] | 0.357 |
| zai: confirmed rate, kev-0.8b-ft-s17 | 28 | 28 | 3.902 | 4.506 | 0.562 | [0.386, 0.734] | 0.464 |
| zai: semantic mean p, kev-0.8b-ft-s17 | 28 | 28 | 0.070 | 0.066 | 0.496 | [0.360, 0.653] | 0.571 |
| zai: confirmed rate, kev-0.8b-ft-s18 | 28 | 28 | 3.783 | 4.214 | 0.541 | [0.368, 0.717] | 0.429 |
| zai: semantic mean p, kev-0.8b-ft-s18 | 28 | 28 | 0.083 | 0.076 | 0.496 | [0.352, 0.665] | 0.571 |
| zai: confirmed rate, kev-0.8b-ft-s19 | 28 | 28 | 3.807 | 4.281 | 0.553 | [0.371, 0.732] | 0.500 |
| zai: semantic mean p, kev-0.8b-ft-s19 | 28 | 28 | 0.070 | 0.071 | 0.571 | [0.425, 0.732] | 0.571 |
| zai: confirmed rate, kev-4b | 28 | 28 | 0.539 | 0.386 | 0.383 | [0.231, 0.556] | 0.411 |
| zai: semantic mean p, kev-4b | 28 | 28 | 0.279 | 0.277 | 0.487 | [0.372, 0.606] | 0.500 |
| zai: confirmed rate, kev-4b-ft-s17 | 28 | 28 | 4.139 | 4.630 | 0.520 | [0.348, 0.698] | 0.464 |
| zai: semantic mean p, kev-4b-ft-s17 | 28 | 28 | 0.060 | 0.075 | 0.672 | [0.518, 0.819] | 0.643 |
| zai: confirmed rate, kev-4b-ft-s18 | 28 | 28 | 4.186 | 4.622 | 0.492 | [0.312, 0.678] | 0.393 |
| zai: semantic mean p, kev-4b-ft-s18 | 28 | 28 | 0.051 | 0.065 | 0.695 | [0.559, 0.834] | 0.679 |
| zai: confirmed rate, kev-4b-ft-s19 | 28 | 28 | 4.110 | 4.521 | 0.510 | [0.329, 0.694] | 0.393 |
| zai: semantic mean p, kev-4b-ft-s19 | 28 | 28 | 0.058 | 0.069 | 0.636 | [0.474, 0.793] | 0.643 |
| zai: confirmed rate, kev-9b | 28 | 28 | 3.451 | 3.775 | 0.518 | [0.349, 0.685] | 0.500 |
| zai: semantic mean p, kev-9b | 28 | 28 | 0.291 | 0.287 | 0.452 | [0.330, 0.574] | 0.429 |
| zai: confirmed rate, kev-9b-ft-s17 | 28 | 28 | 4.295 | 4.694 | 0.506 | [0.329, 0.691] | 0.464 |
| zai: semantic mean p, kev-9b-ft-s17 | 28 | 28 | 0.040 | 0.050 | 0.716 | [0.588, 0.838] | 0.643 |
| zai: confirmed rate, kev-9b-ft-s18 | 28 | 28 | 4.299 | 4.725 | 0.524 | [0.351, 0.710] | 0.500 |
| zai: semantic mean p, kev-9b-ft-s18 | 28 | 28 | 0.038 | 0.053 | 0.739 | [0.601, 0.871] | 0.786 |
| zai: confirmed rate, kev-9b-ft-s19 | 28 | 28 | 4.277 | 4.691 | 0.520 | [0.343, 0.702] | 0.464 |
| zai: semantic mean p, kev-9b-ft-s19 | 28 | 28 | 0.042 | 0.049 | 0.680 | [0.529, 0.825] | 0.714 |
| zai: confirmed rate, laya-english | 28 | 28 | 0.965 | 1.130 | 0.446 | [0.334, 0.554] | 0.482 |
| zai: semantic mean p, laya-english | 28 | 28 | 0.442 | 0.482 | 0.630 | [0.504, 0.751] | 0.571 |
| zai: confirmed rate, laya-multilingual | 28 | 28 | 0.547 | 0.296 | 0.379 | [0.239, 0.520] | 0.429 |
| zai: semantic mean p, laya-multilingual | 28 | 28 | 0.655 | 0.579 | 0.370 | [0.241, 0.495] | 0.286 |
| zai: confirmed rate, laya-typed-decisions | 28 | 28 | 0.896 | 0.283 | 0.383 | [0.289, 0.466] | 0.339 |
| zai: semantic mean p, laya-typed-decisions | 28 | 28 | 0.473 | 0.475 | 0.534 | [0.429, 0.638] | 0.571 |
| zai: confirmed rate, v3-kev-0.8b-ft-s17 | 28 | 28 | 3.952 | 4.264 | 0.539 | [0.370, 0.714] | 0.536 |
| zai: semantic mean p, v3-kev-0.8b-ft-s17 | 28 | 28 | 0.122 | 0.113 | 0.487 | [0.337, 0.647] | 0.536 |
| zai: confirmed rate, v3-kev-0.8b-ft-s18 | 28 | 28 | 3.835 | 4.447 | 0.580 | [0.406, 0.750] | 0.536 |
| zai: semantic mean p, v3-kev-0.8b-ft-s18 | 28 | 28 | 0.088 | 0.076 | 0.467 | [0.343, 0.607] | 0.536 |
| zai: confirmed rate, v3-kev-0.8b-ft-s19 | 28 | 28 | 4.288 | 4.426 | 0.506 | [0.334, 0.677] | 0.429 |
| zai: semantic mean p, v3-kev-0.8b-ft-s19 | 28 | 28 | 0.082 | 0.073 | 0.471 | [0.324, 0.625] | 0.464 |
| zai: confirmed rate, v3-kev-4b-ft-s17 | 28 | 28 | 4.312 | 4.606 | 0.492 | [0.320, 0.680] | 0.464 |
| zai: semantic mean p, v3-kev-4b-ft-s17 | 28 | 28 | 0.043 | 0.062 | 0.708 | [0.588, 0.828] | 0.750 |
| zai: confirmed rate, v3-kev-4b-ft-s18 | 28 | 28 | 4.229 | 4.630 | 0.503 | [0.323, 0.679] | 0.393 |
| zai: semantic mean p, v3-kev-4b-ft-s18 | 28 | 28 | 0.048 | 0.064 | 0.708 | [0.578, 0.833] | 0.643 |
| zai: confirmed rate, v3-kev-4b-ft-s19 | 28 | 28 | 4.552 | 4.710 | 0.477 | [0.302, 0.661] | 0.429 |
| zai: semantic mean p, v3-kev-4b-ft-s19 | 28 | 28 | 0.035 | 0.044 | 0.645 | [0.517, 0.777] | 0.607 |
| zai: confirmed rate, v3-kev-9b-ft-s17 | 28 | 28 | 4.463 | 4.724 | 0.501 | [0.318, 0.689] | 0.429 |
| zai: semantic mean p, v3-kev-9b-ft-s17 | 28 | 28 | 0.059 | 0.071 | 0.707 | [0.566, 0.839] | 0.643 |
| zai: confirmed rate, v3-kev-9b-ft-s18 | 28 | 28 | 4.322 | 4.760 | 0.529 | [0.354, 0.709] | 0.464 |
| zai: semantic mean p, v3-kev-9b-ft-s18 | 28 | 28 | 0.072 | 0.083 | 0.677 | [0.527, 0.823] | 0.643 |
| zai: confirmed rate, v3-kev-9b-ft-s19 | 28 | 28 | 4.439 | 4.882 | 0.518 | [0.331, 0.708] | 0.464 |
| zai: semantic mean p, v3-kev-9b-ft-s19 | 28 | 28 | 0.052 | 0.061 | 0.696 | [0.556, 0.832] | 0.679 |

## By generator tier

| generator tier / score | human docs | generated docs | human mean | generated mean | AUC | 95% CI | paired win rate |
|---|---|---|---|---|---|---|---|
| frontier: lint rate | 141 | 156 | 6.272 | 6.675 | 0.515 | [0.449, 0.585] | 0.532 |
| frontier: confirmed rate, kev-0.8b | 141 | 156 | 0.071 | 0.090 | 0.506 | [0.468, 0.544] | 0.497 |
| frontier: semantic mean p, kev-0.8b | 141 | 156 | 0.242 | 0.239 | 0.337 | [0.276, 0.397] | 0.301 |
| frontier: confirmed rate, kev-0.8b-ft-s17 | 141 | 156 | 3.585 | 4.351 | 0.585 | [0.522, 0.647] | 0.583 |
| frontier: semantic mean p, kev-0.8b-ft-s17 | 141 | 156 | 0.065 | 0.077 | 0.622 | [0.564, 0.681] | 0.647 |
| frontier: confirmed rate, kev-0.8b-ft-s18 | 141 | 156 | 3.449 | 4.059 | 0.565 | [0.505, 0.626] | 0.571 |
| frontier: semantic mean p, kev-0.8b-ft-s18 | 141 | 156 | 0.074 | 0.083 | 0.610 | [0.553, 0.670] | 0.628 |
| frontier: confirmed rate, kev-0.8b-ft-s19 | 141 | 156 | 3.421 | 4.027 | 0.560 | [0.498, 0.623] | 0.571 |
| frontier: semantic mean p, kev-0.8b-ft-s19 | 141 | 156 | 0.063 | 0.077 | 0.644 | [0.587, 0.703] | 0.667 |
| frontier: confirmed rate, kev-4b | 141 | 156 | 0.539 | 0.499 | 0.489 | [0.434, 0.548] | 0.516 |
| frontier: semantic mean p, kev-4b | 141 | 156 | 0.256 | 0.278 | 0.544 | [0.488, 0.603] | 0.551 |
| frontier: confirmed rate, kev-4b-ft-s17 | 141 | 156 | 3.684 | 4.407 | 0.580 | [0.516, 0.641] | 0.596 |
| frontier: semantic mean p, kev-4b-ft-s17 | 141 | 156 | 0.050 | 0.076 | 0.761 | [0.706, 0.813] | 0.808 |
| frontier: confirmed rate, kev-4b-ft-s18 | 141 | 156 | 3.693 | 4.396 | 0.568 | [0.506, 0.630] | 0.583 |
| frontier: semantic mean p, kev-4b-ft-s18 | 141 | 156 | 0.042 | 0.064 | 0.748 | [0.693, 0.798] | 0.769 |
| frontier: confirmed rate, kev-4b-ft-s19 | 141 | 156 | 3.664 | 4.255 | 0.563 | [0.499, 0.625] | 0.583 |
| frontier: semantic mean p, kev-4b-ft-s19 | 141 | 156 | 0.048 | 0.069 | 0.733 | [0.682, 0.784] | 0.769 |
| frontier: confirmed rate, kev-9b | 141 | 156 | 3.075 | 3.289 | 0.514 | [0.450, 0.576] | 0.526 |
| frontier: semantic mean p, kev-9b | 141 | 156 | 0.264 | 0.281 | 0.476 | [0.414, 0.537] | 0.526 |
| frontier: confirmed rate, kev-9b-ft-s17 | 141 | 156 | 3.741 | 4.496 | 0.582 | [0.518, 0.644] | 0.577 |
| frontier: semantic mean p, kev-9b-ft-s17 | 141 | 156 | 0.030 | 0.046 | 0.745 | [0.693, 0.798] | 0.776 |
| frontier: confirmed rate, kev-9b-ft-s18 | 141 | 156 | 3.749 | 4.543 | 0.587 | [0.525, 0.648] | 0.571 |
| frontier: semantic mean p, kev-9b-ft-s18 | 141 | 156 | 0.029 | 0.047 | 0.773 | [0.723, 0.821] | 0.795 |
| frontier: confirmed rate, kev-9b-ft-s19 | 141 | 156 | 3.741 | 4.497 | 0.581 | [0.518, 0.643] | 0.558 |
| frontier: semantic mean p, kev-9b-ft-s19 | 141 | 156 | 0.030 | 0.045 | 0.751 | [0.698, 0.804] | 0.788 |
| frontier: confirmed rate, laya-english | 141 | 156 | 0.939 | 1.289 | 0.533 | [0.484, 0.582] | 0.596 |
| frontier: semantic mean p, laya-english | 141 | 156 | 0.397 | 0.522 | 0.744 | [0.693, 0.796] | 0.788 |
| frontier: confirmed rate, laya-multilingual | 141 | 156 | 0.523 | 0.280 | 0.444 | [0.389, 0.498] | 0.446 |
| frontier: semantic mean p, laya-multilingual | 141 | 156 | 0.581 | 0.697 | 0.620 | [0.564, 0.673] | 0.641 |
| frontier: confirmed rate, laya-typed-decisions | 141 | 156 | 0.754 | 0.465 | 0.441 | [0.405, 0.478] | 0.420 |
| frontier: semantic mean p, laya-typed-decisions | 141 | 156 | 0.423 | 0.490 | 0.666 | [0.612, 0.718] | 0.667 |
| frontier: confirmed rate, v3-kev-0.8b-ft-s17 | 141 | 156 | 3.552 | 4.029 | 0.545 | [0.484, 0.607] | 0.571 |
| frontier: semantic mean p, v3-kev-0.8b-ft-s17 | 141 | 156 | 0.108 | 0.116 | 0.562 | [0.505, 0.622] | 0.571 |
| frontier: confirmed rate, v3-kev-0.8b-ft-s18 | 141 | 156 | 3.535 | 4.101 | 0.560 | [0.497, 0.625] | 0.603 |
| frontier: semantic mean p, v3-kev-0.8b-ft-s18 | 141 | 156 | 0.076 | 0.078 | 0.538 | [0.482, 0.597] | 0.538 |
| frontier: confirmed rate, v3-kev-0.8b-ft-s19 | 141 | 156 | 3.994 | 4.219 | 0.503 | [0.443, 0.567] | 0.506 |
| frontier: semantic mean p, v3-kev-0.8b-ft-s19 | 141 | 156 | 0.070 | 0.071 | 0.528 | [0.470, 0.589] | 0.500 |
| frontier: confirmed rate, v3-kev-4b-ft-s17 | 141 | 156 | 3.746 | 4.398 | 0.568 | [0.506, 0.630] | 0.596 |
| frontier: semantic mean p, v3-kev-4b-ft-s17 | 141 | 156 | 0.036 | 0.057 | 0.744 | [0.694, 0.795] | 0.776 |
| frontier: confirmed rate, v3-kev-4b-ft-s18 | 141 | 156 | 3.757 | 4.484 | 0.575 | [0.512, 0.635] | 0.596 |
| frontier: semantic mean p, v3-kev-4b-ft-s18 | 141 | 156 | 0.041 | 0.060 | 0.725 | [0.669, 0.780] | 0.756 |
| frontier: confirmed rate, v3-kev-4b-ft-s19 | 141 | 156 | 3.987 | 4.588 | 0.568 | [0.506, 0.629] | 0.603 |
| frontier: semantic mean p, v3-kev-4b-ft-s19 | 141 | 156 | 0.028 | 0.043 | 0.714 | [0.660, 0.768] | 0.776 |
| frontier: confirmed rate, v3-kev-9b-ft-s17 | 141 | 156 | 3.792 | 4.618 | 0.591 | [0.529, 0.653] | 0.609 |
| frontier: semantic mean p, v3-kev-9b-ft-s17 | 141 | 156 | 0.047 | 0.064 | 0.750 | [0.695, 0.802] | 0.769 |
| frontier: confirmed rate, v3-kev-9b-ft-s18 | 141 | 156 | 3.732 | 4.534 | 0.589 | [0.526, 0.652] | 0.603 |
| frontier: semantic mean p, v3-kev-9b-ft-s18 | 141 | 156 | 0.061 | 0.075 | 0.699 | [0.639, 0.756] | 0.718 |
| frontier: confirmed rate, v3-kev-9b-ft-s19 | 141 | 156 | 3.887 | 4.759 | 0.593 | [0.530, 0.655] | 0.583 |
| frontier: semantic mean p, v3-kev-9b-ft-s19 | 141 | 156 | 0.043 | 0.055 | 0.725 | [0.673, 0.777] | 0.769 |
| mid: lint rate | 98 | 113 | 6.044 | 6.961 | 0.573 | [0.498, 0.644] | 0.593 |
| mid: confirmed rate, kev-0.8b | 98 | 113 | 0.073 | 0.044 | 0.494 | [0.449, 0.539] | 0.487 |
| mid: semantic mean p, kev-0.8b | 98 | 113 | 0.225 | 0.237 | 0.373 | [0.301, 0.449] | 0.301 |
| mid: confirmed rate, kev-0.8b-ft-s17 | 98 | 113 | 3.453 | 4.848 | 0.660 | [0.590, 0.729] | 0.673 |
| mid: semantic mean p, kev-0.8b-ft-s17 | 98 | 113 | 0.062 | 0.080 | 0.647 | [0.579, 0.712] | 0.637 |
| mid: confirmed rate, kev-0.8b-ft-s18 | 98 | 113 | 3.346 | 4.715 | 0.651 | [0.580, 0.722] | 0.628 |
| mid: semantic mean p, kev-0.8b-ft-s18 | 98 | 113 | 0.068 | 0.084 | 0.638 | [0.573, 0.706] | 0.664 |
| mid: confirmed rate, kev-0.8b-ft-s19 | 98 | 113 | 3.319 | 4.513 | 0.632 | [0.559, 0.704] | 0.602 |
| mid: semantic mean p, kev-0.8b-ft-s19 | 98 | 113 | 0.056 | 0.076 | 0.674 | [0.605, 0.742] | 0.708 |
| mid: confirmed rate, kev-4b | 98 | 113 | 0.417 | 0.681 | 0.648 | [0.585, 0.712] | 0.646 |
| mid: semantic mean p, kev-4b | 98 | 113 | 0.234 | 0.275 | 0.619 | [0.549, 0.691] | 0.619 |
| mid: confirmed rate, kev-4b-ft-s17 | 98 | 113 | 3.464 | 5.028 | 0.673 | [0.602, 0.743] | 0.637 |
| mid: semantic mean p, kev-4b-ft-s17 | 98 | 113 | 0.043 | 0.077 | 0.838 | [0.785, 0.887] | 0.903 |
| mid: confirmed rate, kev-4b-ft-s18 | 98 | 113 | 3.411 | 4.939 | 0.674 | [0.603, 0.745] | 0.637 |
| mid: semantic mean p, kev-4b-ft-s18 | 98 | 113 | 0.036 | 0.064 | 0.795 | [0.737, 0.848] | 0.841 |
| mid: confirmed rate, kev-4b-ft-s19 | 98 | 113 | 3.444 | 4.859 | 0.659 | [0.588, 0.729] | 0.664 |
| mid: semantic mean p, kev-4b-ft-s19 | 98 | 113 | 0.042 | 0.069 | 0.776 | [0.717, 0.830] | 0.832 |
| mid: confirmed rate, kev-9b | 98 | 113 | 2.926 | 3.546 | 0.585 | [0.509, 0.655] | 0.549 |
| mid: semantic mean p, kev-9b | 98 | 113 | 0.244 | 0.280 | 0.512 | [0.443, 0.579] | 0.513 |
| mid: confirmed rate, kev-9b-ft-s17 | 98 | 113 | 3.476 | 4.919 | 0.674 | [0.603, 0.747] | 0.673 |
| mid: semantic mean p, kev-9b-ft-s17 | 98 | 113 | 0.023 | 0.049 | 0.818 | [0.768, 0.866] | 0.867 |
| mid: confirmed rate, kev-9b-ft-s18 | 98 | 113 | 3.471 | 5.110 | 0.699 | [0.630, 0.767] | 0.699 |
| mid: semantic mean p, kev-9b-ft-s18 | 98 | 113 | 0.024 | 0.048 | 0.830 | [0.778, 0.879] | 0.858 |
| mid: confirmed rate, kev-9b-ft-s19 | 98 | 113 | 3.509 | 5.037 | 0.683 | [0.613, 0.753] | 0.690 |
| mid: semantic mean p, kev-9b-ft-s19 | 98 | 113 | 0.024 | 0.045 | 0.842 | [0.790, 0.890] | 0.885 |
| mid: confirmed rate, laya-english | 98 | 113 | 0.944 | 1.258 | 0.573 | [0.502, 0.644] | 0.615 |
| mid: semantic mean p, laya-english | 98 | 113 | 0.379 | 0.554 | 0.805 | [0.740, 0.863] | 0.805 |
| mid: confirmed rate, laya-multilingual | 98 | 113 | 0.375 | 0.275 | 0.485 | [0.414, 0.554] | 0.487 |
| mid: semantic mean p, laya-multilingual | 98 | 113 | 0.535 | 0.690 | 0.659 | [0.589, 0.732] | 0.619 |
| mid: confirmed rate, laya-typed-decisions | 98 | 113 | 0.618 | 0.199 | 0.442 | [0.397, 0.490] | 0.420 |
| mid: semantic mean p, laya-typed-decisions | 98 | 113 | 0.397 | 0.490 | 0.664 | [0.594, 0.730] | 0.664 |
| mid: confirmed rate, v3-kev-0.8b-ft-s17 | 98 | 113 | 3.351 | 4.559 | 0.635 | [0.563, 0.708] | 0.628 |
| mid: semantic mean p, v3-kev-0.8b-ft-s17 | 98 | 113 | 0.100 | 0.107 | 0.538 | [0.471, 0.608] | 0.496 |
| mid: confirmed rate, v3-kev-0.8b-ft-s18 | 98 | 113 | 3.376 | 4.672 | 0.640 | [0.566, 0.711] | 0.637 |
| mid: semantic mean p, v3-kev-0.8b-ft-s18 | 98 | 113 | 0.069 | 0.072 | 0.523 | [0.455, 0.592] | 0.460 |
| mid: confirmed rate, v3-kev-0.8b-ft-s19 | 98 | 113 | 3.763 | 4.784 | 0.601 | [0.531, 0.673] | 0.575 |
| mid: semantic mean p, v3-kev-0.8b-ft-s19 | 98 | 113 | 0.065 | 0.064 | 0.499 | [0.429, 0.569] | 0.460 |
| mid: confirmed rate, v3-kev-4b-ft-s17 | 98 | 113 | 3.453 | 4.980 | 0.676 | [0.608, 0.745] | 0.664 |
| mid: semantic mean p, v3-kev-4b-ft-s17 | 98 | 113 | 0.031 | 0.056 | 0.809 | [0.756, 0.860] | 0.858 |
| mid: confirmed rate, v3-kev-4b-ft-s18 | 98 | 113 | 3.478 | 5.114 | 0.683 | [0.618, 0.751] | 0.681 |
| mid: semantic mean p, v3-kev-4b-ft-s18 | 98 | 113 | 0.036 | 0.060 | 0.776 | [0.717, 0.836] | 0.779 |
| mid: confirmed rate, v3-kev-4b-ft-s19 | 98 | 113 | 3.759 | 5.192 | 0.659 | [0.593, 0.728] | 0.637 |
| mid: semantic mean p, v3-kev-4b-ft-s19 | 98 | 113 | 0.025 | 0.042 | 0.760 | [0.701, 0.818] | 0.779 |
| mid: confirmed rate, v3-kev-9b-ft-s17 | 98 | 113 | 3.541 | 5.169 | 0.696 | [0.625, 0.765] | 0.681 |
| mid: semantic mean p, v3-kev-9b-ft-s17 | 98 | 113 | 0.040 | 0.065 | 0.776 | [0.715, 0.832] | 0.796 |
| mid: confirmed rate, v3-kev-9b-ft-s18 | 98 | 113 | 3.477 | 5.091 | 0.694 | [0.628, 0.758] | 0.681 |
| mid: semantic mean p, v3-kev-9b-ft-s18 | 98 | 113 | 0.053 | 0.077 | 0.741 | [0.676, 0.804] | 0.752 |
| mid: confirmed rate, v3-kev-9b-ft-s19 | 98 | 113 | 3.675 | 5.233 | 0.686 | [0.618, 0.753] | 0.690 |
| mid: semantic mean p, v3-kev-9b-ft-s19 | 98 | 113 | 0.037 | 0.055 | 0.723 | [0.658, 0.784] | 0.752 |
| small: lint rate | 114 | 130 | 6.313 | 6.628 | 0.510 | [0.434, 0.588] | 0.469 |
| small: confirmed rate, kev-0.8b | 114 | 130 | 0.057 | 0.033 | 0.459 | [0.417, 0.502] | 0.454 |
| small: semantic mean p, kev-0.8b | 114 | 130 | 0.234 | 0.243 | 0.377 | [0.304, 0.446] | 0.323 |
| small: confirmed rate, kev-0.8b-ft-s17 | 114 | 130 | 3.658 | 4.653 | 0.599 | [0.528, 0.671] | 0.569 |
| small: semantic mean p, kev-0.8b-ft-s17 | 114 | 130 | 0.066 | 0.081 | 0.646 | [0.580, 0.708] | 0.715 |
| small: confirmed rate, kev-0.8b-ft-s18 | 114 | 130 | 3.509 | 4.452 | 0.593 | [0.520, 0.667] | 0.569 |
| small: semantic mean p, kev-0.8b-ft-s18 | 114 | 130 | 0.073 | 0.088 | 0.631 | [0.568, 0.694] | 0.692 |
| small: confirmed rate, kev-0.8b-ft-s19 | 114 | 130 | 3.493 | 4.400 | 0.591 | [0.519, 0.665] | 0.585 |
| small: semantic mean p, kev-0.8b-ft-s19 | 114 | 130 | 0.060 | 0.079 | 0.662 | [0.595, 0.723] | 0.723 |
| small: confirmed rate, kev-4b | 114 | 130 | 0.526 | 0.567 | 0.515 | [0.443, 0.589] | 0.519 |
| small: semantic mean p, kev-4b | 114 | 130 | 0.243 | 0.278 | 0.587 | [0.524, 0.644] | 0.608 |
| small: confirmed rate, kev-4b-ft-s17 | 114 | 130 | 3.719 | 4.717 | 0.607 | [0.535, 0.677] | 0.600 |
| small: semantic mean p, kev-4b-ft-s17 | 114 | 130 | 0.048 | 0.076 | 0.769 | [0.707, 0.824] | 0.785 |
| small: confirmed rate, kev-4b-ft-s18 | 114 | 130 | 3.734 | 4.703 | 0.602 | [0.527, 0.673] | 0.546 |
| small: semantic mean p, kev-4b-ft-s18 | 114 | 130 | 0.042 | 0.065 | 0.744 | [0.680, 0.800] | 0.777 |
| small: confirmed rate, kev-4b-ft-s19 | 114 | 130 | 3.717 | 4.616 | 0.594 | [0.520, 0.668] | 0.546 |
| small: semantic mean p, kev-4b-ft-s19 | 114 | 130 | 0.048 | 0.069 | 0.733 | [0.664, 0.794] | 0.715 |
| small: confirmed rate, kev-9b | 114 | 130 | 3.265 | 2.993 | 0.455 | [0.374, 0.534] | 0.462 |
| small: semantic mean p, kev-9b | 114 | 130 | 0.255 | 0.283 | 0.500 | [0.430, 0.570] | 0.523 |
| small: confirmed rate, kev-9b-ft-s17 | 114 | 130 | 3.804 | 4.659 | 0.591 | [0.519, 0.663] | 0.600 |
| small: semantic mean p, kev-9b-ft-s17 | 114 | 130 | 0.031 | 0.047 | 0.746 | [0.679, 0.806] | 0.746 |
| small: confirmed rate, kev-9b-ft-s18 | 114 | 130 | 3.849 | 4.815 | 0.600 | [0.528, 0.673] | 0.569 |
| small: semantic mean p, kev-9b-ft-s18 | 114 | 130 | 0.029 | 0.050 | 0.779 | [0.720, 0.839] | 0.808 |
| small: confirmed rate, kev-9b-ft-s19 | 114 | 130 | 3.832 | 4.778 | 0.603 | [0.531, 0.675] | 0.592 |
| small: semantic mean p, kev-9b-ft-s19 | 114 | 130 | 0.029 | 0.046 | 0.766 | [0.703, 0.826] | 0.777 |
| small: confirmed rate, laya-english | 114 | 130 | 1.048 | 1.230 | 0.572 | [0.507, 0.634] | 0.650 |
| small: semantic mean p, laya-english | 114 | 130 | 0.372 | 0.526 | 0.784 | [0.727, 0.836] | 0.754 |
| small: confirmed rate, laya-multilingual | 114 | 130 | 0.462 | 0.294 | 0.426 | [0.355, 0.497] | 0.404 |
| small: semantic mean p, laya-multilingual | 114 | 130 | 0.558 | 0.663 | 0.600 | [0.531, 0.666] | 0.577 |
| small: confirmed rate, laya-typed-decisions | 114 | 130 | 0.761 | 0.489 | 0.442 | [0.391, 0.492] | 0.423 |
| small: semantic mean p, laya-typed-decisions | 114 | 130 | 0.403 | 0.489 | 0.688 | [0.626, 0.748] | 0.669 |
| small: confirmed rate, v3-kev-0.8b-ft-s17 | 114 | 130 | 3.624 | 4.407 | 0.579 | [0.510, 0.649] | 0.577 |
| small: semantic mean p, v3-kev-0.8b-ft-s17 | 114 | 130 | 0.108 | 0.108 | 0.514 | [0.445, 0.581] | 0.531 |
| small: confirmed rate, v3-kev-0.8b-ft-s18 | 114 | 130 | 3.568 | 4.441 | 0.590 | [0.521, 0.664] | 0.577 |
| small: semantic mean p, v3-kev-0.8b-ft-s18 | 114 | 130 | 0.076 | 0.076 | 0.524 | [0.457, 0.589] | 0.554 |
| small: confirmed rate, v3-kev-0.8b-ft-s19 | 114 | 130 | 3.948 | 4.642 | 0.563 | [0.494, 0.636] | 0.546 |
| small: semantic mean p, v3-kev-0.8b-ft-s19 | 114 | 130 | 0.073 | 0.066 | 0.494 | [0.425, 0.561] | 0.546 |
| small: confirmed rate, v3-kev-4b-ft-s17 | 114 | 130 | 3.764 | 4.639 | 0.590 | [0.517, 0.661] | 0.515 |
| small: semantic mean p, v3-kev-4b-ft-s17 | 114 | 130 | 0.035 | 0.056 | 0.750 | [0.693, 0.804] | 0.785 |
| small: confirmed rate, v3-kev-4b-ft-s18 | 114 | 130 | 3.785 | 4.758 | 0.594 | [0.521, 0.667] | 0.562 |
| small: semantic mean p, v3-kev-4b-ft-s18 | 114 | 130 | 0.041 | 0.061 | 0.741 | [0.682, 0.797] | 0.785 |
| small: confirmed rate, v3-kev-4b-ft-s19 | 114 | 130 | 4.014 | 4.827 | 0.585 | [0.510, 0.659] | 0.554 |
| small: semantic mean p, v3-kev-4b-ft-s19 | 114 | 130 | 0.027 | 0.041 | 0.711 | [0.648, 0.770] | 0.708 |
| small: confirmed rate, v3-kev-9b-ft-s17 | 114 | 130 | 3.923 | 4.801 | 0.592 | [0.519, 0.663] | 0.569 |
| small: semantic mean p, v3-kev-9b-ft-s17 | 114 | 130 | 0.048 | 0.067 | 0.735 | [0.670, 0.792] | 0.738 |
| small: confirmed rate, v3-kev-9b-ft-s18 | 114 | 130 | 3.826 | 4.824 | 0.612 | [0.541, 0.682] | 0.615 |
| small: semantic mean p, v3-kev-9b-ft-s18 | 114 | 130 | 0.061 | 0.079 | 0.700 | [0.632, 0.762] | 0.708 |
| small: confirmed rate, v3-kev-9b-ft-s19 | 114 | 130 | 3.987 | 4.932 | 0.596 | [0.524, 0.670] | 0.585 |
| small: semantic mean p, v3-kev-9b-ft-s19 | 114 | 130 | 0.043 | 0.054 | 0.704 | [0.633, 0.769] | 0.715 |

## Per lint rule

Score: the rule's findings per 100 words. Rules that fired on at least one document.

| rule | held out | human docs firing | generated docs firing | AUC | 95% CI | confirmed AUC, kev-0.8b | confirmed AUC, kev-0.8b-ft-s17 | confirmed AUC, kev-0.8b-ft-s18 | confirmed AUC, kev-0.8b-ft-s19 | confirmed AUC, kev-4b | confirmed AUC, kev-4b-ft-s17 | confirmed AUC, kev-4b-ft-s18 | confirmed AUC, kev-4b-ft-s19 | confirmed AUC, kev-9b | confirmed AUC, kev-9b-ft-s17 | confirmed AUC, kev-9b-ft-s18 | confirmed AUC, kev-9b-ft-s19 | confirmed AUC, laya-english | confirmed AUC, laya-multilingual | confirmed AUC, laya-typed-decisions | confirmed AUC, v3-kev-0.8b-ft-s17 | confirmed AUC, v3-kev-0.8b-ft-s18 | confirmed AUC, v3-kev-0.8b-ft-s19 | confirmed AUC, v3-kev-4b-ft-s17 | confirmed AUC, v3-kev-4b-ft-s18 | confirmed AUC, v3-kev-4b-ft-s19 | confirmed AUC, v3-kev-9b-ft-s17 | confirmed AUC, v3-kev-9b-ft-s18 | confirmed AUC, v3-kev-9b-ft-s19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ai-tells-formatting.title-case-heading | no | 1 | 192 | 0.739 | [0.711, 0.768] | 0.500 | 0.739 | 0.739 | 0.739 | 0.684 | 0.739 | 0.739 | 0.738 | 0.675 | 0.738 | 0.739 | 0.739 | 0.661 | 0.505 | 0.505 | 0.739 | 0.739 | 0.739 | 0.739 | 0.739 | 0.739 | 0.739 | 0.739 | 0.739 |
| prose-craft.sentence-length | no | 129 | 99 | 0.267 | [0.229, 0.308] | 0.501 | 0.318 | 0.321 | 0.319 | 0.500 | 0.327 | 0.342 | 0.301 | 0.428 | 0.308 | 0.326 | 0.321 | 0.444 | 0.465 | 0.454 | 0.288 | 0.298 | 0.299 | 0.293 | 0.292 | 0.289 | 0.309 | 0.298 | 0.306 |
| ste-descriptive.sentence-too-long-descriptive | no | 178 | 257 | 0.275 | [0.236, 0.311] | 0.501 | 0.516 | 0.564 | 0.586 | 0.475 | 0.502 | 0.517 | 0.522 | 0.389 | 0.542 | 0.527 | 0.552 | 0.443 | 0.447 | 0.468 | 0.486 | 0.563 | 0.445 | 0.495 | 0.519 | 0.494 | 0.501 | 0.538 | 0.538 |
| ste-punctuation.colon-terminates-sentence-for-count | yes | 83 | 13 | 0.308 | [0.273, 0.343] | 0.500 | 0.500 | 0.499 | 0.492 | 0.500 | 0.491 | 0.500 | 0.490 | 0.497 | 0.466 | 0.477 | 0.486 | 0.441 | 0.474 | 0.482 | 0.459 | 0.491 | 0.485 | 0.487 | 0.497 | 0.492 | 0.472 | 0.477 | 0.474 |
| prose-craft.future-tense | no | 120 | 123 | 0.348 | [0.309, 0.387] | 0.495 | 0.356 | 0.359 | 0.359 | 0.500 | 0.356 | 0.363 | 0.361 | 0.440 | 0.357 | 0.361 | 0.361 | 0.482 | 0.480 | 0.474 | 0.362 | 0.361 | 0.356 | 0.361 | 0.365 | 0.362 | 0.358 | 0.360 | 0.359 |
| ai-tells-content-shape.superficial-ing-analysis | no | 4 | 118 | 0.640 | [0.614, 0.667] | 0.508 | 0.644 | 0.642 | 0.640 | 0.500 | 0.641 | 0.641 | 0.642 | 0.500 | 0.641 | 0.641 | 0.641 | 0.513 | 0.500 | 0.501 | 0.642 | 0.642 | 0.641 | 0.641 | 0.641 | 0.641 | 0.641 | 0.641 | 0.641 |
| prose-craft.spacing | no | 65 | 23 | 0.369 | [0.334, 0.402] | 0.500 | 0.385 | 0.380 | 0.387 | 0.497 | 0.389 | 0.392 | 0.380 | 0.441 | 0.392 | 0.394 | 0.385 | 0.483 | 0.492 | 0.490 | 0.385 | 0.387 | 0.392 | 0.385 | 0.387 | 0.387 | 0.399 | 0.392 | 0.390 |
| ste-words.approved-word-substitution | no | 81 | 218 | 0.616 | [0.575, 0.654] | 0.497 | 0.624 | 0.623 | 0.626 | 0.497 | 0.626 | 0.623 | 0.623 | 0.503 | 0.630 | 0.627 | 0.635 | 0.523 | 0.496 | 0.483 | 0.632 | 0.624 | 0.620 | 0.619 | 0.613 | 0.629 | 0.624 | 0.628 | 0.630 |
| prose-format.no-unicode-dash | yes | 16 | 121 | 0.612 | [0.587, 0.641] | 0.500 | 0.592 | 0.513 | 0.534 | 0.501 | 0.585 | 0.542 | 0.563 | 0.561 | 0.604 | 0.600 | 0.603 | 0.534 | 0.500 | 0.506 | 0.599 | 0.539 | 0.563 | 0.570 | 0.589 | 0.589 | 0.611 | 0.611 | 0.612 |
| prose-inflation.slop-lexicon | no | 20 | 123 | 0.609 | [0.576, 0.639] | 0.499 | 0.606 | 0.612 | 0.604 | 0.500 | 0.604 | 0.607 | 0.610 | 0.574 | 0.611 | 0.611 | 0.610 | 0.534 | 0.498 | 0.501 | 0.612 | 0.608 | 0.609 | 0.610 | 0.605 | 0.613 | 0.613 | 0.611 | 0.612 |
| ai-tells-formatting.bold-spray | no | 3 | 92 | 0.608 | [0.588, 0.629] | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.521 | 0.500 | 0.497 | 0.500 | 0.544 | 0.520 | 0.508 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 |
| ste-descriptive.paragraph-too-many-sentences | no | 68 | 51 | 0.400 | [0.365, 0.434] | 0.491 | 0.442 | 0.472 | 0.443 | 0.460 | 0.447 | 0.436 | 0.429 | 0.451 | 0.447 | 0.458 | 0.446 | 0.492 | 0.490 | 0.478 | 0.443 | 0.464 | 0.454 | 0.439 | 0.445 | 0.432 | 0.473 | 0.477 | 0.457 |
| ste-nouns.multiword-noun-too-long | no | 124 | 278 | 0.599 | [0.556, 0.638] | 0.502 | 0.503 | 0.539 | 0.507 | 0.515 | 0.566 | 0.574 | 0.580 | 0.502 | 0.561 | 0.578 | 0.558 | 0.552 | 0.506 | 0.511 | 0.515 | 0.542 | 0.521 | 0.532 | 0.590 | 0.542 | 0.544 | 0.564 | 0.538 |
| prose-inflation.intensifier | yes | 47 | 16 | 0.402 | [0.371, 0.433] | 0.497 | 0.414 | 0.431 | 0.427 | 0.500 | 0.406 | 0.409 | 0.404 | 0.405 | 0.405 | 0.404 | 0.400 | 0.474 | 0.494 | 0.480 | 0.442 | 0.426 | 0.432 | 0.404 | 0.402 | 0.402 | 0.407 | 0.404 | 0.400 |
| ste-sentences.complex-text-not-in-vertical-list | no | 106 | 253 | 0.595 | [0.554, 0.635] | 0.506 | 0.526 | 0.524 | 0.515 | 0.521 | 0.530 | 0.524 | 0.519 | 0.541 | 0.526 | 0.538 | 0.522 | 0.543 | 0.528 | 0.505 | 0.511 | 0.512 | 0.511 | 0.513 | 0.513 | 0.512 | 0.530 | 0.528 | 0.538 |
| orwell.compound-preposition | yes | 39 | 8 | 0.412 | [0.384, 0.439] | 0.500 | 0.416 | 0.416 | 0.419 | 0.500 | 0.419 | 0.419 | 0.419 | 0.423 | 0.417 | 0.417 | 0.417 | 0.480 | 0.499 | 0.485 | 0.419 | 0.421 | 0.416 | 0.422 | 0.421 | 0.420 | 0.420 | 0.420 | 0.417 |
| prose-craft.dead-opener | no | 44 | 19 | 0.413 | [0.382, 0.443] | 0.500 | 0.418 | 0.418 | 0.418 | 0.470 | 0.421 | 0.421 | 0.421 | 0.440 | 0.418 | 0.418 | 0.418 | 0.494 | 0.492 | 0.495 | 0.418 | 0.418 | 0.418 | 0.418 | 0.421 | 0.421 | 0.418 | 0.418 | 0.418 |
| orwell.unsupported-evaluative | no | 7 | 81 | 0.586 | [0.561, 0.611] | 0.503 | 0.588 | 0.588 | 0.587 | 0.500 | 0.585 | 0.588 | 0.588 | 0.509 | 0.588 | 0.588 | 0.588 | 0.516 | 0.500 | 0.504 | 0.588 | 0.587 | 0.588 | 0.588 | 0.588 | 0.588 | 0.588 | 0.588 | 0.588 |
| ai-tells-formatting.inline-header-list | no | 0 | 68 | 0.585 | [0.565, 0.608] | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.500 | 0.501 | 0.500 | 0.500 | 0.500 | 0.533 | 0.513 | 0.503 | 0.503 | 0.503 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.500 |
| prose-craft.directional-ref | no | 38 | 10 | 0.417 | [0.389, 0.446] | 0.497 | 0.428 | 0.431 | 0.431 | 0.495 | 0.423 | 0.423 | 0.426 | 0.434 | 0.428 | 0.428 | 0.426 | 0.480 | 0.497 | 0.485 | 0.431 | 0.431 | 0.427 | 0.426 | 0.423 | 0.421 | 0.431 | 0.428 | 0.426 |
| ste-verbs.complex-tense | no | 130 | 172 | 0.419 | [0.376, 0.465] | 0.494 | 0.451 | 0.443 | 0.444 | 0.480 | 0.435 | 0.432 | 0.451 | 0.436 | 0.436 | 0.438 | 0.443 | 0.526 | 0.483 | 0.480 | 0.449 | 0.462 | 0.442 | 0.448 | 0.435 | 0.437 | 0.460 | 0.451 | 0.439 |
| prose-craft.first-person-plural | no | 79 | 88 | 0.429 | [0.390, 0.467] | 0.500 | 0.439 | 0.440 | 0.435 | 0.517 | 0.445 | 0.440 | 0.443 | 0.485 | 0.445 | 0.443 | 0.447 | 0.497 | 0.484 | 0.468 | 0.435 | 0.437 | 0.435 | 0.445 | 0.445 | 0.438 | 0.442 | 0.443 | 0.452 |
| ste-procedural.multiple-instructions-per-sentence | no | 62 | 71 | 0.435 | [0.397, 0.467] | 0.500 | 0.503 | 0.521 | 0.521 | 0.501 | 0.509 | 0.510 | 0.513 | 0.497 | 0.505 | 0.515 | 0.509 | 0.499 | 0.489 | 0.491 | 0.509 | 0.514 | 0.508 | 0.504 | 0.509 | 0.520 | 0.513 | 0.505 | 0.506 |
| prose-format.prose-block | no | 39 | 24 | 0.436 | [0.406, 0.462] | 0.500 | 0.506 | 0.500 | 0.503 | 0.503 | 0.504 | 0.494 | 0.506 | 0.500 | 0.504 | 0.503 | 0.510 | 0.475 | 0.490 | 0.495 | 0.498 | 0.503 | 0.503 | 0.509 | 0.514 | 0.511 | 0.504 | 0.505 | 0.501 |
| prose-craft.unclear-antecedent | yes | 62 | 73 | 0.438 | [0.402, 0.474] | 0.500 | 0.485 | 0.489 | 0.476 | 0.497 | 0.468 | 0.471 | 0.461 | 0.487 | 0.462 | 0.455 | 0.461 | 0.495 | 0.494 | 0.494 | 0.467 | 0.472 | 0.475 | 0.457 | 0.453 | 0.464 | 0.448 | 0.446 | 0.459 |
| ste-procedural.sentence-too-long-procedural | no | 43 | 38 | 0.442 | [0.411, 0.472] | 0.500 | 0.503 | 0.508 | 0.510 | 0.489 | 0.498 | 0.505 | 0.504 | 0.499 | 0.505 | 0.506 | 0.505 | 0.494 | 0.492 | 0.501 | 0.495 | 0.507 | 0.504 | 0.499 | 0.503 | 0.509 | 0.506 | 0.506 | 0.509 |
| ai-tells-content-shape.durable-vocabulary-habits | yes | 8 | 57 | 0.552 | [0.530, 0.575] | 0.500 | 0.555 | 0.557 | 0.554 | 0.503 | 0.551 | 0.550 | 0.549 | 0.546 | 0.555 | 0.555 | 0.549 | 0.503 | 0.499 | 0.500 | 0.555 | 0.555 | 0.555 | 0.553 | 0.550 | 0.550 | 0.551 | 0.550 | 0.551 |
| prose-inflation.vague-quantifier | no | 92 | 194 | 0.551 | [0.509, 0.594] | 0.496 | 0.545 | 0.548 | 0.554 | 0.501 | 0.550 | 0.553 | 0.549 | 0.515 | 0.542 | 0.555 | 0.555 | 0.500 | 0.501 | 0.491 | 0.550 | 0.551 | 0.552 | 0.554 | 0.553 | 0.549 | 0.550 | 0.551 | 0.552 |
| prose-craft.politeness | yes | 39 | 35 | 0.453 | [0.425, 0.482] | 0.500 | 0.459 | 0.458 | 0.458 | 0.500 | 0.483 | 0.491 | 0.495 | 0.476 | 0.498 | 0.485 | 0.500 | 0.501 | 0.495 | 0.494 | 0.457 | 0.461 | 0.458 | 0.485 | 0.498 | 0.488 | 0.491 | 0.486 | 0.476 |
| ste-practices.omitted-conjunction-that | no | 40 | 108 | 0.546 | [0.518, 0.574] | 0.502 | 0.527 | 0.527 | 0.500 | 0.500 | 0.517 | 0.512 | 0.512 | 0.493 | 0.516 | 0.524 | 0.503 | 0.514 | 0.503 | 0.500 | 0.518 | 0.524 | 0.520 | 0.512 | 0.522 | 0.546 | 0.519 | 0.529 | 0.528 |
| prose-craft.ambiguity | no | 18 | 0 | 0.455 | [0.432, 0.472] | 0.500 | 0.463 | 0.463 | 0.460 | 0.500 | 0.465 | 0.465 | 0.465 | 0.500 | 0.465 | 0.465 | 0.463 | 0.500 | 0.500 | 0.497 | 0.463 | 0.463 | 0.460 | 0.465 | 0.463 | 0.465 | 0.463 | 0.463 | 0.463 |
| prose-craft.optional-plural | no | 18 | 0 | 0.455 | [0.435, 0.472] | 0.500 | 0.460 | 0.465 | 0.460 | 0.500 | 0.458 | 0.460 | 0.458 | 0.492 | 0.463 | 0.460 | 0.463 | 0.500 | 0.497 | 0.497 | 0.465 | 0.460 | 0.460 | 0.458 | 0.458 | 0.458 | 0.460 | 0.460 | 0.463 |
| docs-discipline.status-language | no | 49 | 59 | 0.456 | [0.425, 0.486] | 0.499 | 0.469 | 0.474 | 0.467 | 0.500 | 0.474 | 0.468 | 0.476 | 0.501 | 0.470 | 0.457 | 0.479 | 0.495 | 0.485 | 0.495 | 0.467 | 0.473 | 0.479 | 0.474 | 0.483 | 0.471 | 0.466 | 0.468 | 0.465 |
| prose-craft.self-reference | no | 21 | 7 | 0.456 | [0.433, 0.477] | 0.500 | 0.478 | 0.481 | 0.474 | 0.500 | 0.483 | 0.478 | 0.475 | 0.471 | 0.475 | 0.475 | 0.479 | 0.500 | 0.500 | 0.497 | 0.486 | 0.485 | 0.493 | 0.485 | 0.484 | 0.483 | 0.494 | 0.485 | 0.485 |
| ai-tells-formatting.em-dash-density | no | 5 | 40 | 0.538 | [0.522, 0.554] | 0.497 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.519 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.497 | 0.497 | 0.500 |
| ste-verbs.passive-voice | no | 185 | 352 | 0.464 | [0.421, 0.508] | 0.475 | 0.541 | 0.519 | 0.515 | 0.440 | 0.531 | 0.525 | 0.521 | 0.495 | 0.506 | 0.512 | 0.496 | 0.444 | 0.414 | 0.445 | 0.502 | 0.492 | 0.477 | 0.530 | 0.525 | 0.503 | 0.511 | 0.513 | 0.513 |
| ste-practices.possessive-form-unclear | no | 23 | 17 | 0.466 | [0.441, 0.489] | 0.500 | 0.500 | 0.500 | 0.497 | 0.500 | 0.497 | 0.500 | 0.500 | 0.500 | 0.497 | 0.497 | 0.500 | 0.495 | 0.497 | 0.500 | 0.497 | 0.499 | 0.501 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 |
| ste-punctuation.semicolon-used | no | 70 | 109 | 0.466 | [0.428, 0.506] | 0.490 | 0.471 | 0.474 | 0.471 | 0.500 | 0.475 | 0.474 | 0.475 | 0.494 | 0.481 | 0.481 | 0.477 | 0.514 | 0.506 | 0.498 | 0.471 | 0.471 | 0.471 | 0.477 | 0.474 | 0.472 | 0.478 | 0.476 | 0.475 |
| ste-words.obligation-word-substitution | no | 80 | 160 | 0.530 | [0.494, 0.568] | 0.505 | 0.521 | 0.514 | 0.499 | 0.500 | 0.507 | 0.513 | 0.495 | 0.531 | 0.499 | 0.523 | 0.498 | 0.506 | 0.501 | 0.489 | 0.499 | 0.516 | 0.516 | 0.500 | 0.512 | 0.521 | 0.517 | 0.530 | 0.523 |
| ste-verbs.auxiliary-stacking | no | 14 | 4 | 0.470 | [0.453, 0.485] | 0.501 | 0.470 | 0.473 | 0.470 | 0.500 | 0.470 | 0.470 | 0.470 | 0.500 | 0.470 | 0.470 | 0.470 | 0.492 | 0.500 | 0.500 | 0.475 | 0.470 | 0.473 | 0.470 | 0.470 | 0.470 | 0.470 | 0.470 | 0.470 |
| ai-tells-structure.contrastive-inversion-frames | no | 1 | 25 | 0.529 | [0.515, 0.543] | 0.501 | 0.521 | 0.524 | 0.526 | 0.500 | 0.524 | 0.525 | 0.525 | 0.514 | 0.526 | 0.525 | 0.525 | 0.508 | 0.501 | 0.503 | 0.523 | 0.526 | 0.525 | 0.520 | 0.524 | 0.524 | 0.525 | 0.526 | 0.526 |
| ai-tells-structure.summary-closer-frames | no | 2 | 26 | 0.528 | [0.512, 0.541] | 0.500 | 0.526 | 0.528 | 0.530 | 0.500 | 0.527 | 0.527 | 0.527 | 0.503 | 0.527 | 0.529 | 0.529 | 0.501 | 0.497 | 0.500 | 0.527 | 0.528 | 0.526 | 0.527 | 0.527 | 0.527 | 0.526 | 0.529 | 0.529 |
| prose-craft.ordinals | no | 14 | 6 | 0.472 | [0.455, 0.489] | 0.500 | 0.501 | 0.499 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.481 | 0.501 | 0.501 | 0.501 | 0.500 | 0.497 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.499 | 0.499 | 0.499 |
| prose-discipline.bidirectional-hedge | no | 4 | 30 | 0.528 | [0.510, 0.543] | 0.500 | 0.515 | 0.510 | 0.515 | 0.500 | 0.523 | 0.525 | 0.523 | 0.515 | 0.521 | 0.525 | 0.526 | 0.501 | 0.503 | 0.500 | 0.519 | 0.520 | 0.523 | 0.514 | 0.523 | 0.523 | 0.520 | 0.523 | 0.519 |
| ste-sentences.missing-article-or-determiner | no | 4 | 29 | 0.526 | [0.509, 0.544] | 0.500 | 0.501 | 0.500 | 0.501 | 0.500 | 0.504 | 0.500 | 0.508 | 0.506 | 0.501 | 0.504 | 0.504 | 0.508 | 0.500 | 0.500 | 0.501 | 0.505 | 0.501 | 0.509 | 0.509 | 0.505 | 0.509 | 0.505 | 0.505 |
| prose-discipline.hedged-hedge | yes | 22 | 22 | 0.474 | [0.449, 0.500] | 0.500 | 0.480 | 0.481 | 0.478 | 0.500 | 0.480 | 0.485 | 0.476 | 0.479 | 0.475 | 0.481 | 0.490 | 0.500 | 0.497 | 0.497 | 0.479 | 0.476 | 0.479 | 0.474 | 0.484 | 0.471 | 0.474 | 0.474 | 0.475 |
| prose-craft.wordiness | no | 76 | 127 | 0.475 | [0.434, 0.514] | 0.500 | 0.476 | 0.472 | 0.458 | 0.452 | 0.475 | 0.478 | 0.474 | 0.468 | 0.475 | 0.472 | 0.468 | 0.489 | 0.490 | 0.479 | 0.466 | 0.488 | 0.470 | 0.473 | 0.478 | 0.479 | 0.470 | 0.475 | 0.469 |
| docs-discipline.history-narration | yes | 30 | 38 | 0.476 | [0.450, 0.503] | 0.497 | 0.490 | 0.491 | 0.491 | 0.500 | 0.485 | 0.481 | 0.489 | 0.492 | 0.483 | 0.488 | 0.484 | 0.498 | 0.500 | 0.494 | 0.483 | 0.493 | 0.489 | 0.479 | 0.481 | 0.483 | 0.481 | 0.492 | 0.480 |
| prose-inflation.borderline-hype | no | 60 | 96 | 0.477 | [0.443, 0.510] | 0.500 | 0.519 | 0.525 | 0.517 | 0.500 | 0.521 | 0.521 | 0.516 | 0.498 | 0.533 | 0.532 | 0.525 | 0.499 | 0.497 | 0.486 | 0.520 | 0.518 | 0.510 | 0.501 | 0.507 | 0.502 | 0.509 | 0.515 | 0.515 |
| ste-punctuation.hyphen-missing-in-compound-modifier | no | 18 | 17 | 0.477 | [0.454, 0.498] | 0.500 | 0.484 | 0.488 | 0.482 | 0.500 | 0.495 | 0.495 | 0.496 | 0.491 | 0.494 | 0.494 | 0.493 | 0.500 | 0.501 | 0.501 | 0.485 | 0.495 | 0.481 | 0.501 | 0.495 | 0.495 | 0.492 | 0.489 | 0.494 |
| prose-craft.plural-abbreviation | no | 10 | 2 | 0.478 | [0.461, 0.491] | 0.495 | 0.478 | 0.478 | 0.478 | 0.489 | 0.480 | 0.485 | 0.485 | 0.478 | 0.483 | 0.483 | 0.481 | 0.500 | 0.492 | 0.500 | 0.478 | 0.478 | 0.478 | 0.488 | 0.483 | 0.478 | 0.495 | 0.493 | 0.483 |
| ste-practices.phrasal-verb | yes | 16 | 14 | 0.478 | [0.457, 0.498] | 0.500 | 0.484 | 0.481 | 0.486 | 0.500 | 0.487 | 0.486 | 0.486 | 0.483 | 0.485 | 0.493 | 0.488 | 0.495 | 0.497 | 0.500 | 0.480 | 0.480 | 0.478 | 0.487 | 0.488 | 0.488 | 0.493 | 0.490 | 0.494 |
| prose-discipline.run-on | no | 10 | 3 | 0.479 | [0.463, 0.494] | 0.497 | 0.496 | 0.503 | 0.500 | 0.500 | 0.495 | 0.498 | 0.493 | 0.498 | 0.498 | 0.500 | 0.499 | 0.499 | 0.497 | 0.497 | 0.495 | 0.496 | 0.494 | 0.495 | 0.500 | 0.493 | 0.498 | 0.498 | 0.499 |
| ai-tells-structure.cataphoric-lead-in-core | yes | 12 | 7 | 0.479 | [0.460, 0.496] | 0.500 | 0.484 | 0.481 | 0.476 | 0.500 | 0.480 | 0.476 | 0.480 | 0.476 | 0.476 | 0.474 | 0.479 | 0.499 | 0.500 | 0.500 | 0.476 | 0.483 | 0.479 | 0.486 | 0.475 | 0.483 | 0.475 | 0.474 | 0.474 |
| docs-discipline.internal-refs | no | 9 | 4 | 0.483 | [0.465, 0.496] | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.495 | 0.497 | 0.497 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.497 | 0.497 | 0.497 | 0.492 | 0.495 | 0.495 | 0.500 | 0.497 | 0.500 |
| prose-craft.hyphens | no | 9 | 4 | 0.483 | [0.468, 0.498] | 0.500 | 0.490 | 0.480 | 0.487 | 0.492 | 0.479 | 0.479 | 0.479 | 0.484 | 0.479 | 0.479 | 0.479 | 0.500 | 0.501 | 0.500 | 0.480 | 0.480 | 0.482 | 0.479 | 0.479 | 0.479 | 0.479 | 0.481 | 0.479 |
| prose-craft.relative-date | yes | 40 | 64 | 0.483 | [0.456, 0.511] | 0.499 | 0.503 | 0.479 | 0.494 | 0.492 | 0.498 | 0.497 | 0.503 | 0.489 | 0.497 | 0.493 | 0.495 | 0.500 | 0.493 | 0.489 | 0.496 | 0.485 | 0.480 | 0.496 | 0.497 | 0.497 | 0.495 | 0.498 | 0.489 |
| ste-procedural.instruction-not-imperative | no | 34 | 81 | 0.517 | [0.486, 0.546] | 0.500 | 0.491 | 0.498 | 0.487 | 0.493 | 0.504 | 0.496 | 0.490 | 0.521 | 0.507 | 0.492 | 0.505 | 0.505 | 0.500 | 0.493 | 0.486 | 0.504 | 0.491 | 0.522 | 0.522 | 0.518 | 0.526 | 0.518 | 0.512 |
| ste-punctuation.hyphen-group-too-long | no | 10 | 7 | 0.484 | [0.467, 0.497] | 0.497 | 0.499 | 0.499 | 0.500 | 0.496 | 0.501 | 0.501 | 0.503 | 0.486 | 0.501 | 0.497 | 0.505 | 0.492 | 0.500 | 0.500 | 0.500 | 0.494 | 0.500 | 0.503 | 0.499 | 0.503 | 0.504 | 0.494 | 0.501 |
| prose-craft.gerund-heading | no | 0 | 13 | 0.516 | [0.508, 0.526] | 0.500 | 0.510 | 0.508 | 0.511 | 0.505 | 0.513 | 0.513 | 0.513 | 0.514 | 0.513 | 0.513 | 0.509 | 0.505 | 0.500 | 0.500 | 0.509 | 0.513 | 0.513 | 0.513 | 0.515 | 0.515 | 0.511 | 0.515 | 0.516 |
| ai-tells-register.intensifier-tics-core | no | 3 | 18 | 0.515 | [0.503, 0.527] | 0.500 | 0.516 | 0.516 | 0.513 | 0.503 | 0.516 | 0.516 | 0.515 | 0.514 | 0.518 | 0.518 | 0.518 | 0.503 | 0.504 | 0.496 | 0.516 | 0.516 | 0.519 | 0.516 | 0.516 | 0.514 | 0.516 | 0.518 | 0.518 |
| ai-tells-content-shape.adjective-per-noun-spray | no | 8 | 5 | 0.486 | [0.471, 0.501] | 0.500 | 0.500 | 0.500 | 0.501 | 0.500 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.495 | 0.499 | 0.501 | 0.500 | 0.500 | 0.500 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 |
| ai-tells-register.corporate-analytic-filler-core | no | 2 | 14 | 0.513 | [0.500, 0.524] | 0.500 | 0.509 | 0.511 | 0.510 | 0.503 | 0.508 | 0.508 | 0.508 | 0.504 | 0.508 | 0.510 | 0.508 | 0.499 | 0.500 | 0.497 | 0.509 | 0.509 | 0.510 | 0.509 | 0.508 | 0.508 | 0.510 | 0.509 | 0.508 |
| prose-promotion.promotional-puffery | no | 0 | 10 | 0.513 | [0.505, 0.521] | 0.500 | 0.513 | 0.513 | 0.513 | 0.500 | 0.513 | 0.513 | 0.513 | 0.509 | 0.513 | 0.513 | 0.513 | 0.503 | 0.500 | 0.500 | 0.513 | 0.513 | 0.513 | 0.513 | 0.513 | 0.513 | 0.513 | 0.513 | 0.513 |
| prose-agency.agentless-passive | no | 5 | 0 | 0.487 | [0.475, 0.497] | 0.500 | 0.490 | 0.495 | 0.487 | 0.500 | 0.487 | 0.490 | 0.487 | 0.497 | 0.487 | 0.490 | 0.487 | 0.500 | 0.500 | 0.497 | 0.487 | 0.490 | 0.490 | 0.487 | 0.487 | 0.487 | 0.487 | 0.490 | 0.487 |
| prose-craft.negative-requirement | no | 2 | 13 | 0.511 | [0.499, 0.524] | 0.500 | 0.510 | 0.510 | 0.510 | 0.500 | 0.510 | 0.509 | 0.511 | 0.503 | 0.509 | 0.510 | 0.509 | 0.501 | 0.497 | 0.500 | 0.510 | 0.510 | 0.510 | 0.510 | 0.510 | 0.509 | 0.509 | 0.510 | 0.510 |
| prose-inflation.nominalized-verb | yes | 7 | 22 | 0.510 | [0.492, 0.528] | 0.500 | 0.515 | 0.514 | 0.512 | 0.501 | 0.511 | 0.509 | 0.514 | 0.500 | 0.503 | 0.500 | 0.509 | 0.500 | 0.500 | 0.500 | 0.517 | 0.510 | 0.510 | 0.514 | 0.511 | 0.508 | 0.513 | 0.513 | 0.510 |
| prose-promotion.promotional-adjective-noun | no | 2 | 12 | 0.510 | [0.499, 0.521] | 0.500 | 0.510 | 0.510 | 0.510 | 0.500 | 0.509 | 0.510 | 0.510 | 0.506 | 0.509 | 0.510 | 0.510 | 0.500 | 0.500 | 0.500 | 0.509 | 0.510 | 0.510 | 0.510 | 0.510 | 0.510 | 0.510 | 0.509 | 0.509 |
| prose-inflation.document-preamble | no | 17 | 41 | 0.510 | [0.489, 0.530] | 0.500 | 0.515 | 0.517 | 0.518 | 0.513 | 0.519 | 0.515 | 0.522 | 0.526 | 0.516 | 0.517 | 0.516 | 0.491 | 0.500 | 0.501 | 0.515 | 0.521 | 0.524 | 0.518 | 0.516 | 0.514 | 0.515 | 0.517 | 0.516 |
| prose-scope.implementation-leak | no | 5 | 3 | 0.491 | [0.481, 0.500] | 0.497 | 0.495 | 0.496 | 0.495 | 0.500 | 0.495 | 0.496 | 0.496 | 0.497 | 0.495 | 0.496 | 0.496 | 0.495 | 0.497 | 0.497 | 0.496 | 0.495 | 0.496 | 0.497 | 0.496 | 0.496 | 0.495 | 0.499 | 0.497 |
| prose-agency.unattributed-recommendation | no | 6 | 5 | 0.491 | [0.478, 0.503] | 0.500 | 0.491 | 0.491 | 0.491 | 0.500 | 0.491 | 0.491 | 0.491 | 0.501 | 0.491 | 0.491 | 0.491 | 0.500 | 0.500 | 0.500 | 0.491 | 0.490 | 0.491 | 0.491 | 0.491 | 0.494 | 0.491 | 0.491 | 0.494 |
| ai-tells-content-shape.fake-specificity | no | 2 | 10 | 0.508 | [0.498, 0.519] | 0.500 | 0.510 | 0.508 | 0.508 | 0.500 | 0.508 | 0.508 | 0.508 | 0.500 | 0.508 | 0.508 | 0.508 | 0.500 | 0.500 | 0.500 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 |
| prose-promotion.promotional-verbs | yes | 1 | 8 | 0.508 | [0.499, 0.515] | 0.500 | 0.510 | 0.510 | 0.510 | 0.500 | 0.510 | 0.510 | 0.510 | 0.503 | 0.510 | 0.510 | 0.510 | 0.501 | 0.500 | 0.500 | 0.510 | 0.510 | 0.510 | 0.510 | 0.510 | 0.510 | 0.510 | 0.510 | 0.510 |
| ai-tells-structure.tricolon-abuse-core | no | 0 | 6 | 0.508 | [0.502, 0.514] | 0.500 | 0.508 | 0.508 | 0.508 | 0.503 | 0.508 | 0.508 | 0.508 | 0.505 | 0.508 | 0.508 | 0.508 | 0.501 | 0.500 | 0.500 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 |
| prose-scope.unrequested-reassurance | no | 4 | 2 | 0.493 | [0.481, 0.502] | 0.500 | 0.495 | 0.495 | 0.495 | 0.500 | 0.495 | 0.495 | 0.495 | 0.499 | 0.495 | 0.495 | 0.495 | 0.500 | 0.497 | 0.500 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.494 |
| prose-inflation.business-jargon | no | 4 | 2 | 0.493 | [0.481, 0.503] | 0.500 | 0.491 | 0.491 | 0.491 | 0.497 | 0.493 | 0.493 | 0.493 | 0.491 | 0.495 | 0.495 | 0.495 | 0.501 | 0.501 | 0.500 | 0.491 | 0.491 | 0.491 | 0.493 | 0.493 | 0.493 | 0.493 | 0.495 | 0.495 |
| prose-discipline.phrasal-verb | no | 3 | 11 | 0.506 | [0.494, 0.519] | 0.500 | 0.504 | 0.506 | 0.506 | 0.501 | 0.504 | 0.508 | 0.505 | 0.504 | 0.506 | 0.505 | 0.506 | 0.500 | 0.501 | 0.497 | 0.508 | 0.508 | 0.508 | 0.508 | 0.505 | 0.508 | 0.509 | 0.504 | 0.508 |
| prose-inflation.uncomparables | no | 3 | 1 | 0.494 | [0.485, 0.501] | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.497 | 0.497 | 0.500 | 0.500 | 0.497 | 0.501 | 0.499 | 0.500 | 0.500 | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.497 | 0.497 | 0.500 | 0.501 | 0.501 |
| prose-craft.redundancy | yes | 4 | 3 | 0.494 | [0.482, 0.504] | 0.500 | 0.494 | 0.494 | 0.494 | 0.500 | 0.495 | 0.495 | 0.495 | 0.492 | 0.494 | 0.494 | 0.492 | 0.500 | 0.497 | 0.497 | 0.494 | 0.492 | 0.494 | 0.495 | 0.495 | 0.495 | 0.495 | 0.494 | 0.494 |
| ai-tells-structure.rhetorical-question-transition | no | 1 | 7 | 0.506 | [0.497, 0.515] | 0.500 | 0.503 | 0.504 | 0.501 | 0.500 | 0.500 | 0.501 | 0.501 | 0.505 | 0.500 | 0.501 | 0.500 | 0.500 | 0.501 | 0.500 | 0.501 | 0.500 | 0.500 | 0.500 | 0.504 | 0.501 | 0.499 | 0.505 | 0.501 |
| ste-procedural.condition-after-command | no | 102 | 200 | 0.506 | [0.461, 0.548] | 0.521 | 0.520 | 0.504 | 0.508 | 0.501 | 0.494 | 0.504 | 0.495 | 0.521 | 0.488 | 0.510 | 0.509 | 0.493 | 0.488 | 0.502 | 0.476 | 0.496 | 0.499 | 0.515 | 0.523 | 0.499 | 0.495 | 0.496 | 0.504 |
| prose-discipline.frozen-verb | no | 13 | 21 | 0.494 | [0.473, 0.515] | 0.501 | 0.490 | 0.490 | 0.493 | 0.494 | 0.490 | 0.489 | 0.495 | 0.504 | 0.491 | 0.489 | 0.491 | 0.503 | 0.496 | 0.499 | 0.490 | 0.490 | 0.495 | 0.494 | 0.489 | 0.493 | 0.491 | 0.489 | 0.491 |
| orwell.stale-figure | no | 2 | 8 | 0.505 | [0.495, 0.515] | 0.500 | 0.505 | 0.505 | 0.505 | 0.500 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.508 | 0.500 | 0.500 | 0.500 | 0.505 | 0.505 | 0.505 | 0.508 | 0.505 | 0.505 | 0.508 | 0.508 | 0.508 |
| prose-craft.misnomer | no | 3 | 2 | 0.495 | [0.485, 0.504] | 0.500 | 0.494 | 0.494 | 0.494 | 0.501 | 0.495 | 0.497 | 0.495 | 0.494 | 0.494 | 0.495 | 0.495 | 0.501 | 0.500 | 0.500 | 0.495 | 0.494 | 0.494 | 0.494 | 0.495 | 0.494 | 0.495 | 0.494 | 0.494 |
| ai-tells-figurative.figurative-draws | no | 0 | 4 | 0.505 | [0.501, 0.510] | 0.500 | 0.504 | 0.504 | 0.505 | 0.500 | 0.504 | 0.503 | 0.504 | 0.501 | 0.501 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.504 | 0.503 | 0.504 | 0.501 | 0.504 | 0.503 | 0.501 | 0.501 | 0.500 |
| ai-tells-structure.meta-narration-frames | no | 0 | 4 | 0.505 | [0.501, 0.510] | 0.500 | 0.504 | 0.503 | 0.503 | 0.500 | 0.503 | 0.503 | 0.504 | 0.503 | 0.503 | 0.505 | 0.503 | 0.500 | 0.500 | 0.500 | 0.505 | 0.504 | 0.505 | 0.505 | 0.505 | 0.505 | 0.505 | 0.505 | 0.505 |
| ai-tells-structure.absolute-assertion-core | yes | 2 | 0 | 0.495 | [0.487, 0.500] | 0.500 | 0.495 | 0.497 | 0.495 | 0.500 | 0.497 | 0.495 | 0.495 | 0.500 | 0.495 | 0.495 | 0.495 | 0.497 | 0.500 | 0.500 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 |
| prose-craft.articles | no | 2 | 0 | 0.495 | [0.487, 0.500] | 0.500 | 0.497 | 0.497 | 0.495 | 0.500 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.500 | 0.500 | 0.497 | 0.495 | 0.497 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 | 0.495 |
| ai-tells-formatting.italicised-copula | yes | 5 | 6 | 0.495 | [0.480, 0.507] | 0.500 | 0.499 | 0.497 | 0.495 | 0.500 | 0.494 | 0.496 | 0.496 | 0.494 | 0.491 | 0.496 | 0.494 | 0.494 | 0.497 | 0.492 | 0.496 | 0.494 | 0.495 | 0.498 | 0.495 | 0.496 | 0.494 | 0.495 | 0.493 |
| prose-inflation.apologizing | no | 4 | 4 | 0.495 | [0.484, 0.505] | 0.500 | 0.501 | 0.501 | 0.503 | 0.500 | 0.496 | 0.499 | 0.496 | 0.500 | 0.496 | 0.501 | 0.499 | 0.500 | 0.497 | 0.500 | 0.501 | 0.501 | 0.501 | 0.499 | 0.499 | 0.499 | 0.499 | 0.499 | 0.499 |
| prose-craft.versions | no | 8 | 12 | 0.495 | [0.479, 0.509] | 0.500 | 0.495 | 0.494 | 0.494 | 0.500 | 0.495 | 0.494 | 0.494 | 0.491 | 0.495 | 0.494 | 0.496 | 0.496 | 0.500 | 0.495 | 0.496 | 0.495 | 0.494 | 0.493 | 0.494 | 0.495 | 0.498 | 0.494 | 0.495 |
| prose-scope.rejected-alternative | no | 6 | 8 | 0.495 | [0.481, 0.508] | 0.501 | 0.497 | 0.497 | 0.496 | 0.500 | 0.496 | 0.496 | 0.496 | 0.500 | 0.496 | 0.495 | 0.499 | 0.503 | 0.500 | 0.503 | 0.496 | 0.495 | 0.496 | 0.496 | 0.497 | 0.496 | 0.497 | 0.497 | 0.497 |
| ste-words.noun-used-as-verb | yes | 2 | 7 | 0.504 | [0.494, 0.514] | 0.500 | 0.509 | 0.509 | 0.509 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.508 | 0.504 | 0.505 | 0.506 | 0.500 | 0.504 | 0.509 | 0.509 | 0.509 | 0.504 | 0.504 | 0.505 | 0.509 | 0.504 | 0.509 |
| ai-tells-structure.negative-inventory-core | no | 6 | 9 | 0.496 | [0.482, 0.510] | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.498 | 0.499 | 0.498 | 0.500 | 0.498 | 0.501 | 0.495 | 0.500 | 0.500 | 0.500 | 0.499 | 0.496 | 0.498 | 0.496 | 0.498 | 0.496 | 0.498 | 0.501 | 0.501 |
| prose-inflation.hedge-stack | no | 7 | 16 | 0.503 | [0.486, 0.518] | 0.501 | 0.503 | 0.503 | 0.503 | 0.500 | 0.505 | 0.505 | 0.505 | 0.498 | 0.503 | 0.503 | 0.503 | 0.500 | 0.497 | 0.500 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.501 | 0.503 | 0.503 | 0.503 |
| orwell.not-un | no | 4 | 10 | 0.503 | [0.491, 0.514] | 0.500 | 0.503 | 0.505 | 0.503 | 0.500 | 0.503 | 0.505 | 0.505 | 0.505 | 0.506 | 0.505 | 0.504 | 0.499 | 0.500 | 0.497 | 0.500 | 0.506 | 0.506 | 0.508 | 0.506 | 0.505 | 0.506 | 0.505 | 0.505 |
| prose-inflation.additive-hedge | no | 2 | 6 | 0.503 | [0.494, 0.511] | 0.500 | 0.502 | 0.505 | 0.504 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.503 | 0.504 | 0.500 | 0.497 | 0.500 | 0.497 | 0.502 | 0.502 | 0.500 | 0.502 | 0.501 | 0.501 | 0.506 | 0.504 | 0.505 |
| ai-tells-figurative.figurative-sits | no | 0 | 2 | 0.503 | [0.500, 0.506] | 0.500 | 0.503 | 0.503 | 0.501 | 0.500 | 0.503 | 0.501 | 0.501 | 0.500 | 0.503 | 0.503 | 0.503 | 0.500 | 0.500 | 0.500 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.501 | 0.503 |
| ai-tells-register.anthropomorphised-justification-core | no | 0 | 2 | 0.503 | [0.500, 0.506] | 0.500 | 0.503 | 0.501 | 0.501 | 0.500 | 0.501 | 0.503 | 0.501 | 0.500 | 0.500 | 0.501 | 0.500 | 0.500 | 0.500 | 0.500 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.501 |
| ai-tells-structure.definitional-negation-pair | yes | 0 | 2 | 0.503 | [0.500, 0.506] | 0.500 | 0.503 | 0.503 | 0.503 | 0.500 | 0.503 | 0.503 | 0.503 | 0.501 | 0.503 | 0.503 | 0.503 | 0.501 | 0.500 | 0.500 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.503 | 0.501 | 0.503 |
| ai-tells-structure.vague-attribution-core | no | 0 | 2 | 0.503 | [0.500, 0.506] | 0.500 | 0.503 | 0.503 | 0.503 | 0.500 | 0.503 | 0.501 | 0.503 | 0.501 | 0.501 | 0.503 | 0.501 | 0.500 | 0.500 | 0.500 | 0.503 | 0.503 | 0.503 | 0.501 | 0.503 | 0.503 | 0.501 | 0.501 | 0.501 |
| ai-tells-figurative.figurative-falls | yes | 1 | 0 | 0.497 | [0.492, 0.500] | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.500 | 0.500 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 |
| ai-tells-figurative.figurative-runs | no | 1 | 0 | 0.497 | [0.490, 0.500] | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.500 | 0.500 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 |
| ai-tells-formatting.cross-reference-signposting | no | 1 | 0 | 0.497 | [0.492, 0.500] | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.497 | 0.497 | 0.497 | 0.500 | 0.497 | 0.500 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 | 0.497 |
| ste-words.verb-used-as-noun | no | 1 | 0 | 0.497 | [0.492, 0.500] | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 |
| prose-discipline.marketing-lexicon | no | 4 | 9 | 0.501 | [0.490, 0.513] | 0.500 | 0.503 | 0.504 | 0.501 | 0.501 | 0.503 | 0.503 | 0.503 | 0.500 | 0.503 | 0.505 | 0.503 | 0.497 | 0.495 | 0.500 | 0.503 | 0.503 | 0.500 | 0.503 | 0.503 | 0.503 | 0.503 | 0.505 | 0.505 |
| ai-tells-figurative.figurative-wins | no | 0 | 1 | 0.501 | [0.500, 0.504] | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 |
| ai-tells-figurative.resonate-overuse | no | 0 | 1 | 0.501 | [0.500, 0.504] | 0.500 | 0.500 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 |
| ai-tells-register.faux-candor-core | no | 0 | 1 | 0.501 | [0.500, 0.504] | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 |
| ai-tells-structure.fragment-question-pivot | no | 0 | 1 | 0.501 | [0.500, 0.504] | 0.500 | 0.500 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.500 | 0.500 | 0.500 | 0.501 |
| ai-tells-structure.staccato-negative-parallel-frames | no | 0 | 1 | 0.501 | [0.500, 0.504] | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 |
| prose-agency.narrator-distance | no | 0 | 1 | 0.501 | [0.500, 0.504] | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 |
| prose-craft.link-text | yes | 0 | 1 | 0.501 | [0.500, 0.504] | 0.500 | 0.500 | 0.501 | 0.500 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 |
| prose-inflation.vague-declarative | no | 0 | 1 | 0.501 | [0.500, 0.505] | 0.500 | 0.501 | 0.501 | 0.501 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 | 0.501 |
| prose-scope.epigram | no | 0 | 1 | 0.501 | [0.500, 0.505] | 0.500 | 0.500 | 0.501 | 0.500 | 0.500 | 0.500 | 0.500 | 0.501 | 0.500 | 0.501 | 0.500 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.501 | 0.500 | 0.501 | 0.500 | 0.501 | 0.501 |
| ste-verbs.nominalized-action | no | 48 | 91 | 0.501 | [0.466, 0.533] | 0.496 | 0.519 | 0.507 | 0.505 | 0.501 | 0.495 | 0.490 | 0.492 | 0.510 | 0.489 | 0.480 | 0.485 | 0.496 | 0.494 | 0.491 | 0.505 | 0.506 | 0.519 | 0.500 | 0.496 | 0.498 | 0.504 | 0.489 | 0.496 |
| ste-practices.false-friend-term | no | 43 | 80 | 0.500 | [0.472, 0.532] | 0.500 | 0.501 | 0.510 | 0.499 | 0.500 | 0.499 | 0.499 | 0.494 | 0.497 | 0.494 | 0.498 | 0.502 | 0.495 | 0.499 | 0.490 | 0.499 | 0.495 | 0.519 | 0.501 | 0.489 | 0.501 | 0.493 | 0.501 | 0.493 |
| prose-agency.anthropomorphism | yes | 3 | 6 | 0.500 | [0.490, 0.510] | 0.500 | 0.500 | 0.502 | 0.500 | 0.500 | 0.501 | 0.500 | 0.501 | 0.501 | 0.502 | 0.501 | 0.501 | 0.499 | 0.497 | 0.500 | 0.500 | 0.501 | 0.502 | 0.501 | 0.500 | 0.501 | 0.502 | 0.501 | 0.502 |
| ai-tells-structure.think-of-it-as-core | no | 2 | 4 | 0.500 | [0.491, 0.508] | 0.500 | 0.500 | 0.501 | 0.499 | 0.500 | 0.499 | 0.500 | 0.499 | 0.504 | 0.499 | 0.501 | 0.501 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.499 | 0.499 | 0.499 | 0.499 | 0.500 | 0.499 | 0.500 |
| ste-sentences.omitted-subject | yes | 1 | 2 | 0.500 | [0.492, 0.505] | 0.500 | 0.503 | 0.503 | 0.503 | 0.500 | 0.500 | 0.501 | 0.499 | 0.500 | 0.503 | 0.503 | 0.501 | 0.500 | 0.500 | 0.497 | 0.503 | 0.503 | 0.503 | 0.499 | 0.499 | 0.499 | 0.500 | 0.503 | 0.503 |

## Per semantic rule, kev-0.8b

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| ai-tells-structure.false-range | yes | 0.005 | 0.005 | 0.185 | [0.151, 0.220] |
| ai-tells-structure.summary-closer-remainder | no | 0.000 | 0.000 | 0.200 | [0.162, 0.236] |
| ai-tells-structure.audience-straddle-remainder | no | 0.039 | 0.002 | 0.227 | [0.189, 0.263] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.000 | 0.000 | 0.248 | [0.210, 0.288] |
| ai-tells-register.organic-consequence-remainder | no | 0.009 | 0.002 | 0.258 | [0.218, 0.300] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.005 | 0.002 | 0.264 | [0.226, 0.300] |
| ste-descriptive.paragraph-without-related-information | no | 0.002 | 0.016 | 0.269 | [0.233, 0.310] |
| ste-descriptive.missing-key-word-structure | no | 0.002 | 0.001 | 0.272 | [0.234, 0.306] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.002 | 0.001 | 0.280 | [0.242, 0.319] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.000 | 0.280 | [0.244, 0.318] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.002 | 0.002 | 0.288 | [0.248, 0.335] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.021 | 0.004 | 0.298 | [0.259, 0.341] |
| prose-discipline.competing-actor-terms | no | 0.007 | 0.001 | 0.302 | [0.263, 0.342] |
| prose-discipline.hedged-into-uselessness | no | 0.007 | 0.003 | 0.305 | [0.266, 0.345] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.002 | 0.000 | 0.316 | [0.277, 0.360] |
| ai-tells-structure.hollow-acknowledgment | no | 0.034 | 0.024 | 0.323 | [0.284, 0.359] |
| ai-tells-content-shape.padded-symmetry | no | 0.000 | 0.000 | 0.324 | [0.282, 0.368] |
| ai-tells-content-shape.one-point-dilution | no | 0.002 | 0.003 | 0.326 | [0.287, 0.368] |
| ai-tells-content-shape.over-writing-remainder | no | 0.007 | 0.001 | 0.345 | [0.305, 0.386] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.007 | 0.007 | 0.348 | [0.307, 0.391] |
| ai-tells-register.faux-candor-remainder | no | 0.053 | 0.024 | 0.352 | [0.313, 0.391] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.000 | 0.000 | 0.353 | [0.310, 0.396] |
| ai-tells-structure.invented-concept-label | yes | 0.016 | 0.003 | 0.353 | [0.310, 0.399] |
| ai-tells-structure.false-suspense-remainder | no | 0.016 | 0.008 | 0.368 | [0.324, 0.414] |
| prose-discipline.marketing-register | no | 0.005 | 0.001 | 0.369 | [0.332, 0.408] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.011 | 0.000 | 0.374 | [0.338, 0.406] |
| ste-punctuation.parentheses-misuse | no | 0.000 | 0.003 | 0.375 | [0.333, 0.419] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.014 | 0.012 | 0.380 | [0.340, 0.417] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.011 | 0.003 | 0.382 | [0.344, 0.421] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.016 | 0.003 | 0.392 | [0.346, 0.438] |
| ai-tells-register.hedged-symmetry | no | 0.016 | 0.007 | 0.395 | [0.357, 0.432] |
| ai-tells-content-shape.elegant-variation | no | 0.064 | 0.021 | 0.398 | [0.354, 0.440] |
| ste-verbs.gerund-outside-noun-use | no | 0.000 | 0.002 | 0.599 | [0.555, 0.645] |
| ai-tells-structure.analogy-stack-authority | no | 0.007 | 0.001 | 0.406 | [0.367, 0.451] |
| ai-tells-register.over-formatting-reflex | no | 0.002 | 0.008 | 0.409 | [0.368, 0.450] |
| orwell.concrete-floor | no | 0.005 | 0.003 | 0.415 | [0.370, 0.461] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.037 | 0.029 | 0.417 | [0.388, 0.450] |
| ste-verbs.past-participle-not-adjectival | no | 0.005 | 0.001 | 0.419 | [0.377, 0.460] |
| ai-tells-structure.meta-narration-remainder | yes | 0.005 | 0.011 | 0.423 | [0.383, 0.465] |
| prose-discipline.overloaded-sentence | yes | 0.018 | 0.019 | 0.426 | [0.385, 0.470] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.009 | 0.001 | 0.434 | [0.392, 0.475] |
| ste-nouns.long-domain-term-without-short-form | no | 0.023 | 0.026 | 0.435 | [0.394, 0.476] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.028 | 0.031 | 0.437 | [0.393, 0.481] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.021 | 0.012 | 0.440 | [0.400, 0.488] |
| ste-sentences.sentence-not-short-or-clear | no | 0.018 | 0.015 | 0.447 | [0.411, 0.484] |
| ste-descriptive.information-not-gradual | yes | 0.000 | 0.001 | 0.447 | [0.402, 0.492] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.030 | 0.025 | 0.552 | [0.511, 0.591] |
| ste-practices.ambiguous-preposition-with | no | 0.009 | 0.010 | 0.450 | [0.405, 0.497] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.000 | 0.543 | [0.497, 0.592] |
| ai-tells-structure.vague-attribution-remainder | no | 0.000 | 0.000 | 0.537 | [0.495, 0.584] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.009 | 0.008 | 0.530 | [0.486, 0.579] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.041 | 0.036 | 0.484 | [0.448, 0.519] |
| ai-tells-structure.anaphora-abuse | no | 0.007 | 0.003 | 0.485 | [0.439, 0.532] |
| ai-tells-structure.heading-echo | no | 0.002 | 0.002 | 0.511 | [0.464, 0.557] |
| ai-tells-register.false-agency-remainder | no | 0.028 | 0.018 | 0.504 | [0.455, 0.554] |

## Per semantic rule, kev-0.8b-ft-s17

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.172 | 0.589 | 0.857 | [0.825, 0.888] |
| prose-discipline.overloaded-sentence | yes | 0.005 | 0.024 | 0.721 | [0.682, 0.763] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.016 | 0.011 | 0.282 | [0.247, 0.320] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.014 | 0.039 | 0.705 | [0.662, 0.751] |
| ai-tells-structure.heading-echo | no | 0.014 | 0.088 | 0.683 | [0.648, 0.719] |
| ai-tells-structure.analogy-stack-authority | no | 0.005 | 0.001 | 0.318 | [0.280, 0.359] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.028 | 0.003 | 0.320 | [0.283, 0.361] |
| ste-descriptive.information-not-gradual | yes | 0.009 | 0.003 | 0.672 | [0.628, 0.713] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.023 | 0.022 | 0.654 | [0.605, 0.705] |
| ai-tells-structure.false-range | yes | 0.032 | 0.010 | 0.350 | [0.307, 0.398] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.076 | 0.040 | 0.352 | [0.311, 0.396] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.641 | [0.597, 0.688] |
| ai-tells-structure.invented-concept-label | yes | 0.005 | 0.001 | 0.360 | [0.319, 0.404] |
| ai-tells-register.hedged-symmetry | no | 0.025 | 0.013 | 0.367 | [0.324, 0.408] |
| ste-sentences.sentence-not-short-or-clear | no | 0.046 | 0.135 | 0.630 | [0.589, 0.672] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.005 | 0.018 | 0.630 | [0.581, 0.680] |
| ai-tells-structure.vague-attribution-remainder | no | 0.032 | 0.041 | 0.627 | [0.578, 0.678] |
| ai-tells-structure.false-suspense-remainder | no | 0.000 | 0.003 | 0.624 | [0.580, 0.668] |
| ai-tells-register.false-agency-remainder | no | 0.021 | 0.035 | 0.623 | [0.577, 0.671] |
| ai-tells-content-shape.padded-symmetry | no | 0.011 | 0.032 | 0.618 | [0.578, 0.658] |
| prose-discipline.marketing-register | no | 0.014 | 0.034 | 0.618 | [0.580, 0.659] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.005 | 0.003 | 0.393 | [0.346, 0.444] |
| ai-tells-structure.summary-closer-remainder | no | 0.000 | 0.014 | 0.597 | [0.552, 0.646] |
| ai-tells-content-shape.one-point-dilution | no | 0.011 | 0.059 | 0.595 | [0.556, 0.633] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.026 | 0.594 | [0.552, 0.635] |
| ste-punctuation.parentheses-misuse | no | 0.005 | 0.002 | 0.408 | [0.361, 0.455] |
| ai-tells-register.organic-consequence-remainder | no | 0.023 | 0.020 | 0.411 | [0.365, 0.459] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.007 | 0.415 | [0.372, 0.457] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.051 | 0.069 | 0.584 | [0.540, 0.632] |
| ai-tells-register.over-formatting-reflex | no | 0.124 | 0.174 | 0.578 | [0.536, 0.625] |
| ai-tells-content-shape.elegant-variation | no | 0.057 | 0.016 | 0.422 | [0.378, 0.463] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.011 | 0.008 | 0.425 | [0.381, 0.469] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.014 | 0.003 | 0.575 | [0.537, 0.615] |
| ste-verbs.past-participle-not-adjectival | no | 0.048 | 0.058 | 0.573 | [0.534, 0.613] |
| ai-tells-content-shape.over-writing-remainder | no | 0.057 | 0.026 | 0.431 | [0.393, 0.471] |
| ai-tells-structure.audience-straddle-remainder | no | 0.014 | 0.007 | 0.441 | [0.395, 0.486] |
| ste-nouns.long-domain-term-without-short-form | no | 0.005 | 0.001 | 0.553 | [0.508, 0.595] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.018 | 0.012 | 0.552 | [0.510, 0.594] |
| ste-verbs.gerund-outside-noun-use | no | 0.016 | 0.004 | 0.550 | [0.506, 0.591] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.002 | 0.002 | 0.462 | [0.416, 0.510] |
| ai-tells-structure.anaphora-abuse | no | 0.000 | 0.000 | 0.537 | [0.497, 0.580] |
| ste-descriptive.paragraph-without-related-information | no | 0.046 | 0.019 | 0.466 | [0.424, 0.514] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.002 | 0.466 | [0.417, 0.519] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.000 | 0.003 | 0.532 | [0.482, 0.584] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.011 | 0.007 | 0.532 | [0.484, 0.577] |
| prose-discipline.competing-actor-terms | no | 0.002 | 0.005 | 0.479 | [0.440, 0.517] |
| ai-tells-structure.meta-narration-remainder | yes | 0.037 | 0.041 | 0.479 | [0.436, 0.524] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.011 | 0.010 | 0.519 | [0.475, 0.560] |
| ai-tells-register.faux-candor-remainder | no | 0.021 | 0.020 | 0.483 | [0.443, 0.523] |
| prose-discipline.hedged-into-uselessness | no | 0.021 | 0.015 | 0.484 | [0.438, 0.525] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.011 | 0.013 | 0.515 | [0.475, 0.555] |
| ste-descriptive.missing-key-word-structure | no | 0.011 | 0.023 | 0.485 | [0.440, 0.531] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.009 | 0.003 | 0.513 | [0.467, 0.555] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.011 | 0.005 | 0.512 | [0.465, 0.557] |
| ai-tells-structure.hollow-acknowledgment | no | 0.005 | 0.005 | 0.489 | [0.444, 0.532] |

## Per semantic rule, kev-0.8b-ft-s18

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.143 | 0.589 | 0.878 | [0.847, 0.905] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.005 | 0.003 | 0.269 | [0.231, 0.311] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.030 | 0.035 | 0.689 | [0.645, 0.733] |
| ai-tells-structure.false-suspense-remainder | no | 0.011 | 0.028 | 0.684 | [0.640, 0.723] |
| prose-discipline.overloaded-sentence | yes | 0.016 | 0.068 | 0.683 | [0.636, 0.727] |
| prose-discipline.marketing-register | no | 0.025 | 0.047 | 0.680 | [0.637, 0.724] |
| ai-tells-register.organic-consequence-remainder | no | 0.092 | 0.043 | 0.332 | [0.291, 0.376] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.023 | 0.003 | 0.349 | [0.311, 0.394] |
| ai-tells-content-shape.one-point-dilution | no | 0.016 | 0.080 | 0.651 | [0.611, 0.694] |
| ai-tells-structure.false-range | yes | 0.007 | 0.003 | 0.352 | [0.312, 0.393] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.085 | 0.033 | 0.358 | [0.315, 0.403] |
| ai-tells-register.false-agency-remainder | no | 0.014 | 0.023 | 0.641 | [0.594, 0.690] |
| ai-tells-structure.audience-straddle-remainder | no | 0.023 | 0.007 | 0.372 | [0.327, 0.417] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.003 | 0.373 | [0.329, 0.415] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.009 | 0.018 | 0.377 | [0.335, 0.422] |
| ste-descriptive.information-not-gradual | yes | 0.007 | 0.001 | 0.621 | [0.575, 0.667] |
| ai-tells-structure.heading-echo | no | 0.067 | 0.140 | 0.619 | [0.575, 0.659] |
| ai-tells-structure.vague-attribution-remainder | no | 0.018 | 0.010 | 0.614 | [0.564, 0.662] |
| ai-tells-structure.analogy-stack-authority | no | 0.009 | 0.002 | 0.389 | [0.348, 0.435] |
| ste-punctuation.parentheses-misuse | no | 0.000 | 0.000 | 0.401 | [0.360, 0.442] |
| ai-tells-structure.summary-closer-remainder | no | 0.005 | 0.012 | 0.591 | [0.546, 0.635] |
| ste-verbs.gerund-outside-noun-use | no | 0.023 | 0.011 | 0.590 | [0.551, 0.629] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.011 | 0.020 | 0.590 | [0.541, 0.642] |
| ste-descriptive.missing-key-word-structure | no | 0.041 | 0.023 | 0.413 | [0.367, 0.462] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.000 | 0.007 | 0.585 | [0.542, 0.631] |
| ai-tells-content-shape.padded-symmetry | no | 0.007 | 0.015 | 0.581 | [0.535, 0.625] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.021 | 0.009 | 0.573 | [0.525, 0.620] |
| ste-sentences.sentence-not-short-or-clear | no | 0.069 | 0.091 | 0.572 | [0.529, 0.618] |
| ai-tells-content-shape.over-writing-remainder | no | 0.057 | 0.029 | 0.429 | [0.398, 0.463] |
| ai-tells-register.hedged-symmetry | no | 0.009 | 0.010 | 0.434 | [0.389, 0.483] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.016 | 0.024 | 0.558 | [0.514, 0.601] |
| ai-tells-structure.anaphora-abuse | no | 0.011 | 0.010 | 0.558 | [0.512, 0.603] |
| prose-discipline.competing-actor-terms | no | 0.005 | 0.006 | 0.443 | [0.398, 0.485] |
| ai-tells-register.faux-candor-remainder | no | 0.044 | 0.048 | 0.555 | [0.515, 0.600] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.009 | 0.008 | 0.449 | [0.413, 0.486] |
| ai-tells-structure.invented-concept-label | yes | 0.000 | 0.000 | 0.450 | [0.409, 0.491] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.025 | 0.029 | 0.549 | [0.509, 0.585] |
| ste-nouns.long-domain-term-without-short-form | no | 0.002 | 0.001 | 0.541 | [0.498, 0.581] |
| ai-tells-register.over-formatting-reflex | no | 0.071 | 0.118 | 0.538 | [0.495, 0.585] |
| ste-descriptive.paragraph-without-related-information | no | 0.011 | 0.003 | 0.463 | [0.417, 0.512] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.011 | 0.009 | 0.466 | [0.420, 0.512] |
| ai-tells-structure.hollow-acknowledgment | no | 0.007 | 0.009 | 0.534 | [0.493, 0.575] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.002 | 0.004 | 0.469 | [0.424, 0.515] |
| ai-tells-content-shape.elegant-variation | no | 0.025 | 0.016 | 0.469 | [0.421, 0.512] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.005 | 0.005 | 0.530 | [0.478, 0.582] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.039 | 0.014 | 0.527 | [0.489, 0.570] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.011 | 0.006 | 0.474 | [0.431, 0.520] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.030 | 0.526 | [0.485, 0.568] |
| ai-tells-structure.meta-narration-remainder | yes | 0.048 | 0.063 | 0.481 | [0.435, 0.529] |
| ste-verbs.past-participle-not-adjectival | no | 0.041 | 0.023 | 0.484 | [0.443, 0.524] |
| prose-discipline.hedged-into-uselessness | no | 0.018 | 0.013 | 0.488 | [0.441, 0.535] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.005 | 0.005 | 0.508 | [0.461, 0.550] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.507 | [0.461, 0.554] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.014 | 0.000 | 0.504 | [0.462, 0.549] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.007 | 0.002 | 0.497 | [0.449, 0.543] |

## Per semantic rule, kev-0.8b-ft-s19

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.094 | 0.547 | 0.903 | [0.877, 0.926] |
| prose-discipline.overloaded-sentence | yes | 0.005 | 0.036 | 0.715 | [0.673, 0.756] |
| prose-discipline.marketing-register | no | 0.014 | 0.049 | 0.714 | [0.674, 0.757] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.018 | 0.033 | 0.709 | [0.662, 0.755] |
| ai-tells-register.false-agency-remainder | no | 0.016 | 0.026 | 0.700 | [0.656, 0.744] |
| ste-descriptive.information-not-gradual | yes | 0.007 | 0.007 | 0.688 | [0.648, 0.727] |
| ste-sentences.sentence-not-short-or-clear | no | 0.041 | 0.078 | 0.681 | [0.638, 0.728] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.016 | 0.023 | 0.672 | [0.628, 0.722] |
| ai-tells-structure.false-suspense-remainder | no | 0.007 | 0.022 | 0.669 | [0.625, 0.712] |
| ai-tells-structure.heading-echo | no | 0.007 | 0.054 | 0.667 | [0.629, 0.707] |
| ai-tells-structure.analogy-stack-authority | no | 0.009 | 0.002 | 0.341 | [0.305, 0.380] |
| ai-tells-register.organic-consequence-remainder | no | 0.074 | 0.032 | 0.349 | [0.304, 0.400] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.007 | 0.016 | 0.647 | [0.596, 0.697] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.014 | 0.010 | 0.360 | [0.318, 0.399] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.002 | 0.002 | 0.361 | [0.318, 0.403] |
| ai-tells-structure.vague-attribution-remainder | no | 0.037 | 0.068 | 0.639 | [0.592, 0.688] |
| ai-tells-register.hedged-symmetry | no | 0.021 | 0.006 | 0.386 | [0.344, 0.429] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.011 | 0.009 | 0.613 | [0.572, 0.657] |
| ai-tells-structure.false-range | yes | 0.005 | 0.000 | 0.394 | [0.350, 0.439] |
| ai-tells-content-shape.one-point-dilution | no | 0.025 | 0.087 | 0.606 | [0.567, 0.651] |
| ai-tells-structure.hollow-acknowledgment | no | 0.000 | 0.006 | 0.602 | [0.559, 0.642] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.007 | 0.009 | 0.600 | [0.554, 0.647] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.001 | 0.598 | [0.554, 0.642] |
| prose-discipline.competing-actor-terms | no | 0.007 | 0.008 | 0.403 | [0.365, 0.444] |
| ai-tells-content-shape.padded-symmetry | no | 0.011 | 0.032 | 0.596 | [0.555, 0.635] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.005 | 0.007 | 0.596 | [0.553, 0.642] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.007 | 0.018 | 0.592 | [0.549, 0.633] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.580 | [0.537, 0.628] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.000 | 0.012 | 0.575 | [0.532, 0.620] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.057 | 0.029 | 0.426 | [0.380, 0.469] |
| ai-tells-structure.anaphora-abuse | no | 0.000 | 0.001 | 0.572 | [0.525, 0.617] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.002 | 0.022 | 0.570 | [0.528, 0.615] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.007 | 0.001 | 0.431 | [0.393, 0.474] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.060 | 0.067 | 0.564 | [0.523, 0.608] |
| ste-nouns.long-domain-term-without-short-form | no | 0.000 | 0.003 | 0.564 | [0.518, 0.603] |
| ste-descriptive.paragraph-without-related-information | no | 0.011 | 0.004 | 0.438 | [0.393, 0.486] |
| ste-verbs.gerund-outside-noun-use | no | 0.005 | 0.003 | 0.561 | [0.517, 0.606] |
| ste-verbs.past-participle-not-adjectival | no | 0.103 | 0.133 | 0.555 | [0.517, 0.594] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.025 | 0.025 | 0.554 | [0.506, 0.604] |
| ai-tells-structure.audience-straddle-remainder | no | 0.025 | 0.004 | 0.448 | [0.395, 0.494] |
| prose-discipline.hedged-into-uselessness | no | 0.007 | 0.019 | 0.548 | [0.504, 0.591] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.011 | 0.007 | 0.454 | [0.410, 0.497] |
| ai-tells-structure.summary-closer-remainder | no | 0.000 | 0.011 | 0.545 | [0.505, 0.584] |
| ai-tells-structure.invented-concept-label | yes | 0.002 | 0.002 | 0.458 | [0.418, 0.497] |
| ste-descriptive.missing-key-word-structure | no | 0.028 | 0.020 | 0.464 | [0.420, 0.514] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.023 | 0.010 | 0.533 | [0.490, 0.576] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.002 | 0.475 | [0.431, 0.520] |
| ai-tells-content-shape.over-writing-remainder | no | 0.067 | 0.029 | 0.478 | [0.441, 0.515] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.002 | 0.007 | 0.481 | [0.432, 0.531] |
| ai-tells-content-shape.elegant-variation | no | 0.009 | 0.005 | 0.488 | [0.443, 0.531] |
| ai-tells-structure.meta-narration-remainder | yes | 0.039 | 0.042 | 0.492 | [0.450, 0.537] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.009 | 0.003 | 0.508 | [0.460, 0.553] |
| ste-punctuation.parentheses-misuse | no | 0.000 | 0.001 | 0.502 | [0.457, 0.544] |
| ai-tells-register.faux-candor-remainder | no | 0.018 | 0.016 | 0.501 | [0.461, 0.549] |
| ai-tells-register.over-formatting-reflex | no | 0.110 | 0.079 | 0.501 | [0.460, 0.544] |

## Per semantic rule, kev-4b

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.094 | 0.492 | 0.855 | [0.828, 0.884] |
| ai-tells-structure.analogy-stack-authority | no | 0.000 | 0.000 | 0.158 | [0.125, 0.192] |
| ste-nouns.long-domain-term-without-short-form | no | 0.023 | 0.120 | 0.774 | [0.738, 0.812] |
| ai-tells-structure.invented-concept-label | yes | 0.014 | 0.010 | 0.240 | [0.206, 0.279] |
| prose-discipline.overloaded-sentence | yes | 0.032 | 0.198 | 0.750 | [0.708, 0.788] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.007 | 0.010 | 0.260 | [0.222, 0.301] |
| ai-tells-structure.false-range | yes | 0.005 | 0.003 | 0.285 | [0.243, 0.329] |
| ai-tells-content-shape.elegant-variation | no | 0.000 | 0.000 | 0.306 | [0.261, 0.354] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.009 | 0.029 | 0.676 | [0.639, 0.716] |
| ai-tells-register.organic-consequence-remainder | no | 0.005 | 0.004 | 0.361 | [0.321, 0.413] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.000 | 0.364 | [0.319, 0.409] |
| ste-descriptive.information-not-gradual | yes | 0.000 | 0.004 | 0.631 | [0.590, 0.677] |
| ai-tells-structure.vague-attribution-remainder | no | 0.000 | 0.000 | 0.369 | [0.327, 0.414] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.000 | 0.000 | 0.371 | [0.331, 0.412] |
| prose-discipline.competing-actor-terms | no | 0.002 | 0.001 | 0.372 | [0.326, 0.418] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.067 | 0.032 | 0.373 | [0.326, 0.421] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.221 | 0.295 | 0.618 | [0.573, 0.663] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.011 | 0.070 | 0.614 | [0.574, 0.654] |
| ste-sentences.sentence-not-short-or-clear | no | 0.016 | 0.083 | 0.612 | [0.566, 0.651] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.021 | 0.010 | 0.389 | [0.356, 0.422] |
| ste-descriptive.paragraph-without-related-information | no | 0.007 | 0.007 | 0.389 | [0.345, 0.437] |
| ste-verbs.gerund-outside-noun-use | no | 0.177 | 0.276 | 0.610 | [0.563, 0.656] |
| ai-tells-content-shape.one-point-dilution | no | 0.011 | 0.061 | 0.607 | [0.567, 0.648] |
| prose-discipline.marketing-register | no | 0.002 | 0.002 | 0.606 | [0.567, 0.645] |
| ai-tells-register.faux-candor-remainder | no | 0.005 | 0.020 | 0.601 | [0.561, 0.639] |
| ai-tells-structure.anaphora-abuse | no | 0.007 | 0.006 | 0.599 | [0.550, 0.645] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.115 | 0.211 | 0.594 | [0.548, 0.639] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.060 | 0.087 | 0.591 | [0.553, 0.630] |
| prose-discipline.hedged-into-uselessness | no | 0.011 | 0.019 | 0.581 | [0.540, 0.622] |
| ai-tells-structure.meta-narration-remainder | yes | 0.014 | 0.025 | 0.581 | [0.537, 0.626] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.009 | 0.024 | 0.581 | [0.536, 0.623] |
| ai-tells-structure.summary-closer-remainder | no | 0.034 | 0.055 | 0.575 | [0.536, 0.618] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.000 | 0.002 | 0.428 | [0.381, 0.477] |
| ai-tells-content-shape.padded-symmetry | no | 0.000 | 0.003 | 0.432 | [0.394, 0.472] |
| ste-practices.ambiguous-preposition-with | no | 0.021 | 0.007 | 0.434 | [0.385, 0.487] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.002 | 0.001 | 0.434 | [0.396, 0.471] |
| ste-verbs.past-participle-not-adjectival | no | 0.041 | 0.034 | 0.436 | [0.393, 0.478] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.074 | 0.084 | 0.561 | [0.516, 0.609] |
| ai-tells-structure.audience-straddle-remainder | no | 0.002 | 0.001 | 0.561 | [0.527, 0.594] |
| ste-punctuation.parentheses-misuse | no | 0.002 | 0.004 | 0.448 | [0.407, 0.489] |
| ai-tells-structure.hollow-acknowledgment | no | 0.083 | 0.097 | 0.547 | [0.509, 0.588] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.000 | 0.000 | 0.545 | [0.498, 0.595] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.455 | [0.415, 0.496] |
| ai-tells-structure.heading-echo | no | 0.055 | 0.116 | 0.541 | [0.493, 0.589] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.003 | 0.534 | [0.484, 0.580] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.001 | 0.467 | [0.430, 0.508] |
| ai-tells-register.hedged-symmetry | no | 0.000 | 0.001 | 0.468 | [0.430, 0.508] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.000 | 0.000 | 0.472 | [0.429, 0.515] |
| ste-descriptive.missing-key-word-structure | no | 0.000 | 0.000 | 0.528 | [0.480, 0.577] |
| ai-tells-register.false-agency-remainder | no | 0.037 | 0.022 | 0.473 | [0.437, 0.508] |
| ai-tells-structure.false-suspense-remainder | no | 0.007 | 0.020 | 0.478 | [0.435, 0.525] |
| ai-tells-content-shape.over-writing-remainder | no | 0.018 | 0.016 | 0.522 | [0.478, 0.569] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.000 | 0.001 | 0.513 | [0.479, 0.549] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.018 | 0.036 | 0.491 | [0.446, 0.538] |
| ai-tells-register.over-formatting-reflex | no | 0.005 | 0.003 | 0.495 | [0.451, 0.542] |

## Per semantic rule, kev-4b-ft-s17

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.154 | 0.754 | 0.921 | [0.896, 0.945] |
| prose-discipline.marketing-register | no | 0.016 | 0.108 | 0.754 | [0.711, 0.792] |
| ste-nouns.long-domain-term-without-short-form | no | 0.002 | 0.007 | 0.751 | [0.703, 0.796] |
| ste-sentences.sentence-not-short-or-clear | no | 0.018 | 0.106 | 0.739 | [0.697, 0.783] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.005 | 0.030 | 0.734 | [0.691, 0.774] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.000 | 0.003 | 0.729 | [0.685, 0.776] |
| ai-tells-structure.vague-attribution-remainder | no | 0.023 | 0.015 | 0.728 | [0.683, 0.771] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.005 | 0.004 | 0.718 | [0.667, 0.764] |
| ai-tells-content-shape.one-point-dilution | no | 0.011 | 0.036 | 0.716 | [0.669, 0.758] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.011 | 0.036 | 0.716 | [0.667, 0.768] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.016 | 0.030 | 0.710 | [0.664, 0.752] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.023 | 0.023 | 0.700 | [0.658, 0.746] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.000 | 0.000 | 0.691 | [0.645, 0.735] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.002 | 0.002 | 0.680 | [0.634, 0.730] |
| ste-practices.ambiguous-preposition-with | no | 0.002 | 0.007 | 0.680 | [0.633, 0.722] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.000 | 0.002 | 0.677 | [0.631, 0.723] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.053 | 0.045 | 0.675 | [0.628, 0.720] |
| ai-tells-content-shape.padded-symmetry | no | 0.005 | 0.023 | 0.675 | [0.629, 0.720] |
| ai-tells-structure.audience-straddle-remainder | no | 0.002 | 0.001 | 0.668 | [0.620, 0.722] |
| ai-tells-register.false-agency-remainder | no | 0.048 | 0.043 | 0.661 | [0.616, 0.702] |
| ai-tells-structure.false-suspense-remainder | no | 0.000 | 0.006 | 0.646 | [0.599, 0.693] |
| ste-verbs.gerund-outside-noun-use | no | 0.007 | 0.014 | 0.643 | [0.597, 0.688] |
| ai-tells-structure.summary-closer-remainder | no | 0.002 | 0.029 | 0.643 | [0.598, 0.687] |
| prose-discipline.overloaded-sentence | yes | 0.154 | 0.235 | 0.638 | [0.591, 0.685] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.000 | 0.010 | 0.634 | [0.587, 0.690] |
| ste-descriptive.information-not-gradual | yes | 0.007 | 0.015 | 0.633 | [0.583, 0.684] |
| ai-tells-structure.heading-echo | no | 0.044 | 0.122 | 0.632 | [0.589, 0.679] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.003 | 0.628 | [0.575, 0.679] |
| prose-discipline.hedged-into-uselessness | no | 0.007 | 0.024 | 0.627 | [0.580, 0.672] |
| ai-tells-structure.meta-narration-remainder | yes | 0.030 | 0.047 | 0.626 | [0.578, 0.672] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.002 | 0.003 | 0.625 | [0.575, 0.675] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.002 | 0.000 | 0.625 | [0.576, 0.675] |
| ste-descriptive.missing-key-word-structure | no | 0.018 | 0.041 | 0.624 | [0.578, 0.673] |
| ai-tells-register.faux-candor-remainder | no | 0.002 | 0.006 | 0.620 | [0.576, 0.663] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.014 | 0.003 | 0.387 | [0.336, 0.440] |
| ai-tells-structure.hollow-acknowledgment | no | 0.005 | 0.018 | 0.610 | [0.570, 0.652] |
| ste-descriptive.paragraph-without-related-information | no | 0.007 | 0.003 | 0.610 | [0.553, 0.665] |
| ste-punctuation.parentheses-misuse | no | 0.009 | 0.001 | 0.608 | [0.558, 0.656] |
| ai-tells-register.hedged-symmetry | no | 0.007 | 0.009 | 0.597 | [0.553, 0.641] |
| ai-tells-register.organic-consequence-remainder | no | 0.021 | 0.033 | 0.593 | [0.550, 0.638] |
| ai-tells-structure.anaphora-abuse | no | 0.002 | 0.005 | 0.586 | [0.531, 0.644] |
| ai-tells-content-shape.elegant-variation | no | 0.014 | 0.016 | 0.586 | [0.532, 0.638] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.000 | 0.575 | [0.526, 0.627] |
| ai-tells-structure.analogy-stack-authority | no | 0.000 | 0.002 | 0.569 | [0.517, 0.621] |
| ai-tells-content-shape.over-writing-remainder | no | 0.037 | 0.050 | 0.557 | [0.520, 0.601] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.003 | 0.546 | [0.496, 0.598] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.000 | 0.016 | 0.479 | [0.430, 0.532] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.007 | 0.016 | 0.521 | [0.475, 0.567] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.002 | 0.001 | 0.481 | [0.426, 0.537] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.103 | 0.062 | 0.483 | [0.436, 0.533] |
| ste-verbs.past-participle-not-adjectival | no | 0.048 | 0.035 | 0.513 | [0.469, 0.558] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.007 | 0.003 | 0.511 | [0.467, 0.557] |
| ai-tells-structure.invented-concept-label | yes | 0.000 | 0.000 | 0.509 | [0.460, 0.563] |
| ai-tells-register.over-formatting-reflex | no | 0.037 | 0.067 | 0.492 | [0.444, 0.548] |
| ai-tells-structure.false-range | yes | 0.000 | 0.001 | 0.505 | [0.452, 0.558] |

## Per semantic rule, kev-4b-ft-s18

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.131 | 0.689 | 0.921 | [0.897, 0.944] |
| ai-tells-structure.vague-attribution-remainder | no | 0.037 | 0.075 | 0.756 | [0.714, 0.797] |
| prose-discipline.marketing-register | no | 0.014 | 0.090 | 0.750 | [0.711, 0.794] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.005 | 0.045 | 0.727 | [0.684, 0.766] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.007 | 0.027 | 0.708 | [0.664, 0.753] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.002 | 0.704 | [0.656, 0.751] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.016 | 0.042 | 0.687 | [0.640, 0.733] |
| ai-tells-content-shape.one-point-dilution | no | 0.007 | 0.027 | 0.684 | [0.638, 0.730] |
| ste-nouns.long-domain-term-without-short-form | no | 0.000 | 0.003 | 0.679 | [0.630, 0.725] |
| ste-sentences.sentence-not-short-or-clear | no | 0.046 | 0.123 | 0.670 | [0.625, 0.715] |
| ai-tells-content-shape.padded-symmetry | no | 0.011 | 0.026 | 0.665 | [0.615, 0.716] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.000 | 0.005 | 0.658 | [0.613, 0.704] |
| ai-tells-structure.summary-closer-remainder | no | 0.002 | 0.035 | 0.657 | [0.610, 0.700] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.000 | 0.000 | 0.653 | [0.612, 0.698] |
| ste-verbs.gerund-outside-noun-use | no | 0.018 | 0.040 | 0.645 | [0.603, 0.688] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.002 | 0.006 | 0.643 | [0.600, 0.692] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.010 | 0.642 | [0.593, 0.694] |
| ai-tells-structure.false-suspense-remainder | no | 0.005 | 0.006 | 0.635 | [0.591, 0.684] |
| prose-discipline.overloaded-sentence | yes | 0.078 | 0.148 | 0.635 | [0.587, 0.682] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.000 | 0.002 | 0.634 | [0.592, 0.679] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.021 | 0.009 | 0.367 | [0.320, 0.414] |
| ste-descriptive.missing-key-word-structure | no | 0.011 | 0.020 | 0.624 | [0.574, 0.672] |
| ai-tells-structure.audience-straddle-remainder | no | 0.000 | 0.000 | 0.619 | [0.575, 0.667] |
| ai-tells-structure.hollow-acknowledgment | no | 0.005 | 0.020 | 0.613 | [0.573, 0.657] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.023 | 0.021 | 0.612 | [0.568, 0.659] |
| ai-tells-register.false-agency-remainder | no | 0.025 | 0.033 | 0.610 | [0.568, 0.653] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.002 | 0.005 | 0.607 | [0.559, 0.658] |
| ai-tells-content-shape.elegant-variation | no | 0.011 | 0.009 | 0.600 | [0.547, 0.651] |
| ai-tells-structure.meta-narration-remainder | yes | 0.032 | 0.055 | 0.596 | [0.548, 0.642] |
| ai-tells-register.organic-consequence-remainder | no | 0.021 | 0.026 | 0.590 | [0.544, 0.640] |
| ai-tells-register.faux-candor-remainder | no | 0.000 | 0.010 | 0.588 | [0.546, 0.632] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.037 | 0.021 | 0.588 | [0.544, 0.636] |
| ste-punctuation.parentheses-misuse | no | 0.014 | 0.004 | 0.587 | [0.539, 0.632] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.053 | 0.017 | 0.418 | [0.370, 0.465] |
| ai-tells-structure.heading-echo | no | 0.039 | 0.097 | 0.578 | [0.529, 0.622] |
| prose-discipline.hedged-into-uselessness | no | 0.007 | 0.019 | 0.577 | [0.530, 0.623] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.001 | 0.575 | [0.527, 0.624] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.005 | 0.019 | 0.430 | [0.382, 0.479] |
| ste-descriptive.information-not-gradual | yes | 0.009 | 0.010 | 0.562 | [0.511, 0.615] |
| ste-descriptive.paragraph-without-related-information | no | 0.005 | 0.002 | 0.440 | [0.390, 0.491] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.001 | 0.559 | [0.510, 0.608] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.002 | 0.001 | 0.441 | [0.390, 0.498] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.001 | 0.554 | [0.507, 0.604] |
| ai-tells-register.hedged-symmetry | no | 0.002 | 0.006 | 0.553 | [0.513, 0.596] |
| ai-tells-content-shape.over-writing-remainder | no | 0.041 | 0.040 | 0.551 | [0.512, 0.592] |
| ai-tells-structure.analogy-stack-authority | no | 0.002 | 0.003 | 0.549 | [0.502, 0.597] |
| ai-tells-structure.false-range | yes | 0.000 | 0.000 | 0.453 | [0.407, 0.505] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.007 | 0.544 | [0.490, 0.593] |
| ai-tells-structure.invented-concept-label | yes | 0.007 | 0.006 | 0.541 | [0.491, 0.594] |
| ai-tells-structure.anaphora-abuse | no | 0.007 | 0.002 | 0.460 | [0.408, 0.515] |
| ste-verbs.past-participle-not-adjectival | no | 0.087 | 0.057 | 0.466 | [0.431, 0.508] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.005 | 0.006 | 0.530 | [0.486, 0.575] |
| ai-tells-register.over-formatting-reflex | no | 0.034 | 0.052 | 0.470 | [0.421, 0.521] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.011 | 0.003 | 0.472 | [0.429, 0.517] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.005 | 0.008 | 0.517 | [0.466, 0.567] |

## Per semantic rule, kev-4b-ft-s19

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.138 | 0.688 | 0.909 | [0.882, 0.935] |
| prose-discipline.marketing-register | no | 0.009 | 0.075 | 0.724 | [0.685, 0.767] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.002 | 0.016 | 0.705 | [0.657, 0.756] |
| ste-nouns.long-domain-term-without-short-form | no | 0.009 | 0.003 | 0.693 | [0.645, 0.738] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.007 | 0.003 | 0.685 | [0.637, 0.734] |
| ai-tells-structure.vague-attribution-remainder | no | 0.018 | 0.015 | 0.684 | [0.643, 0.730] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.016 | 0.023 | 0.680 | [0.638, 0.721] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.000 | 0.000 | 0.670 | [0.628, 0.713] |
| ai-tells-content-shape.one-point-dilution | no | 0.023 | 0.055 | 0.667 | [0.623, 0.713] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.007 | 0.037 | 0.651 | [0.608, 0.692] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.053 | 0.102 | 0.644 | [0.602, 0.689] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.016 | 0.019 | 0.641 | [0.592, 0.691] |
| ste-practices.ambiguous-preposition-with | no | 0.002 | 0.015 | 0.640 | [0.591, 0.688] |
| ste-punctuation.parentheses-misuse | no | 0.005 | 0.001 | 0.633 | [0.590, 0.675] |
| ai-tells-structure.heading-echo | no | 0.071 | 0.152 | 0.627 | [0.582, 0.673] |
| ai-tells-structure.false-suspense-remainder | no | 0.005 | 0.009 | 0.626 | [0.582, 0.671] |
| ai-tells-register.faux-candor-remainder | no | 0.002 | 0.013 | 0.623 | [0.585, 0.664] |
| ste-sentences.sentence-not-short-or-clear | no | 0.032 | 0.112 | 0.620 | [0.571, 0.669] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.005 | 0.004 | 0.616 | [0.565, 0.665] |
| prose-discipline.overloaded-sentence | yes | 0.124 | 0.202 | 0.616 | [0.566, 0.664] |
| ai-tells-content-shape.padded-symmetry | no | 0.000 | 0.016 | 0.615 | [0.565, 0.667] |
| ai-tells-structure.audience-straddle-remainder | no | 0.002 | 0.001 | 0.614 | [0.567, 0.666] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.002 | 0.001 | 0.610 | [0.567, 0.657] |
| ai-tells-structure.meta-narration-remainder | yes | 0.041 | 0.066 | 0.610 | [0.564, 0.657] |
| ai-tells-register.false-agency-remainder | no | 0.030 | 0.023 | 0.609 | [0.567, 0.650] |
| ai-tells-structure.hollow-acknowledgment | no | 0.011 | 0.023 | 0.594 | [0.557, 0.635] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.002 | 0.004 | 0.592 | [0.545, 0.637] |
| ai-tells-structure.summary-closer-remainder | no | 0.002 | 0.033 | 0.592 | [0.544, 0.639] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.001 | 0.587 | [0.540, 0.638] |
| prose-discipline.competing-actor-terms | no | 0.002 | 0.009 | 0.586 | [0.535, 0.639] |
| ai-tells-content-shape.elegant-variation | no | 0.011 | 0.002 | 0.427 | [0.380, 0.473] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.000 | 0.008 | 0.570 | [0.521, 0.622] |
| ai-tells-structure.anaphora-abuse | no | 0.002 | 0.002 | 0.437 | [0.385, 0.494] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.014 | 0.007 | 0.439 | [0.392, 0.492] |
| ste-descriptive.paragraph-without-related-information | no | 0.002 | 0.001 | 0.560 | [0.506, 0.611] |
| ste-verbs.gerund-outside-noun-use | no | 0.023 | 0.029 | 0.559 | [0.510, 0.607] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.030 | 0.012 | 0.443 | [0.396, 0.497] |
| ai-tells-structure.analogy-stack-authority | no | 0.009 | 0.001 | 0.547 | [0.497, 0.600] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.021 | 0.017 | 0.457 | [0.411, 0.503] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.085 | 0.049 | 0.458 | [0.408, 0.509] |
| ai-tells-register.hedged-symmetry | no | 0.009 | 0.007 | 0.541 | [0.501, 0.582] |
| prose-discipline.hedged-into-uselessness | no | 0.002 | 0.018 | 0.540 | [0.495, 0.582] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.006 | 0.539 | [0.488, 0.592] |
| ste-descriptive.missing-key-word-structure | no | 0.018 | 0.018 | 0.537 | [0.485, 0.590] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.005 | 0.001 | 0.472 | [0.416, 0.528] |
| ste-descriptive.information-not-gradual | yes | 0.011 | 0.012 | 0.523 | [0.473, 0.577] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.021 | 0.010 | 0.520 | [0.475, 0.567] |
| ai-tells-register.organic-consequence-remainder | no | 0.046 | 0.047 | 0.516 | [0.471, 0.560] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.007 | 0.024 | 0.486 | [0.439, 0.538] |
| ai-tells-structure.false-range | yes | 0.005 | 0.003 | 0.512 | [0.460, 0.563] |
| ai-tells-content-shape.over-writing-remainder | no | 0.057 | 0.046 | 0.510 | [0.474, 0.549] |
| ai-tells-register.over-formatting-reflex | no | 0.037 | 0.075 | 0.490 | [0.442, 0.542] |
| ai-tells-structure.invented-concept-label | yes | 0.005 | 0.002 | 0.509 | [0.463, 0.556] |
| ste-verbs.past-participle-not-adjectival | no | 0.076 | 0.049 | 0.492 | [0.452, 0.535] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.002 | 0.499 | [0.448, 0.551] |

## Per semantic rule, kev-9b

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.437 | 0.898 | 0.903 | [0.881, 0.925] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.196 | [0.161, 0.231] |
| ai-tells-structure.analogy-stack-authority | no | 0.002 | 0.000 | 0.198 | [0.166, 0.231] |
| ai-tells-content-shape.padded-symmetry | no | 0.000 | 0.001 | 0.210 | [0.174, 0.248] |
| ai-tells-structure.invented-concept-label | yes | 0.090 | 0.030 | 0.211 | [0.180, 0.246] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.000 | 0.000 | 0.224 | [0.187, 0.265] |
| prose-discipline.competing-actor-terms | no | 0.018 | 0.003 | 0.229 | [0.198, 0.263] |
| ai-tells-content-shape.elegant-variation | no | 0.011 | 0.002 | 0.243 | [0.201, 0.286] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.018 | 0.019 | 0.248 | [0.214, 0.283] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.000 | 0.289 | [0.246, 0.340] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.002 | 0.294 | [0.255, 0.333] |
| ai-tells-structure.anaphora-abuse | no | 0.002 | 0.002 | 0.294 | [0.253, 0.334] |
| ai-tells-content-shape.over-writing-remainder | no | 0.069 | 0.075 | 0.294 | [0.254, 0.335] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.069 | 0.030 | 0.302 | [0.257, 0.347] |
| ai-tells-register.faux-candor-remainder | no | 0.014 | 0.047 | 0.694 | [0.654, 0.734] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.000 | 0.003 | 0.310 | [0.274, 0.344] |
| ste-verbs.gerund-outside-noun-use | no | 0.260 | 0.447 | 0.656 | [0.614, 0.700] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.000 | 0.001 | 0.346 | [0.301, 0.395] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.021 | 0.026 | 0.348 | [0.304, 0.390] |
| ai-tells-register.organic-consequence-remainder | no | 0.011 | 0.012 | 0.356 | [0.313, 0.399] |
| prose-discipline.overloaded-sentence | yes | 0.391 | 0.528 | 0.639 | [0.596, 0.678] |
| ste-sentences.sentence-not-short-or-clear | no | 0.037 | 0.137 | 0.627 | [0.578, 0.669] |
| ste-verbs.past-participle-not-adjectival | no | 0.087 | 0.074 | 0.382 | [0.341, 0.421] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.170 | 0.284 | 0.612 | [0.567, 0.659] |
| ste-punctuation.parentheses-misuse | no | 0.110 | 0.088 | 0.394 | [0.354, 0.435] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.552 | 0.613 | 0.603 | [0.557, 0.647] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.322 | 0.247 | 0.399 | [0.362, 0.434] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.002 | 0.015 | 0.399 | [0.354, 0.441] |
| prose-discipline.marketing-register | no | 0.014 | 0.042 | 0.599 | [0.554, 0.644] |
| ai-tells-structure.vague-attribution-remainder | no | 0.000 | 0.003 | 0.402 | [0.359, 0.446] |
| prose-discipline.hedged-into-uselessness | no | 0.023 | 0.027 | 0.409 | [0.370, 0.448] |
| ai-tells-structure.false-suspense-remainder | no | 0.005 | 0.015 | 0.420 | [0.372, 0.463] |
| ai-tells-structure.summary-closer-remainder | no | 0.308 | 0.284 | 0.423 | [0.381, 0.473] |
| ste-descriptive.information-not-gradual | yes | 0.016 | 0.073 | 0.568 | [0.519, 0.609] |
| ste-descriptive.missing-key-word-structure | no | 0.140 | 0.184 | 0.567 | [0.520, 0.612] |
| ai-tells-register.hedged-symmetry | no | 0.000 | 0.002 | 0.433 | [0.397, 0.474] |
| ai-tells-register.false-agency-remainder | no | 0.117 | 0.076 | 0.438 | [0.401, 0.473] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.189 | 0.179 | 0.447 | [0.399, 0.493] |
| ste-practices.ambiguous-preposition-with | no | 0.032 | 0.036 | 0.451 | [0.404, 0.501] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.002 | 0.012 | 0.460 | [0.405, 0.513] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.074 | 0.055 | 0.460 | [0.421, 0.500] |
| ste-nouns.long-domain-term-without-short-form | no | 0.078 | 0.122 | 0.535 | [0.491, 0.577] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.016 | 0.028 | 0.470 | [0.436, 0.506] |
| ai-tells-structure.meta-narration-remainder | yes | 0.041 | 0.068 | 0.470 | [0.426, 0.514] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.000 | 0.000 | 0.472 | [0.424, 0.518] |
| ai-tells-structure.false-range | yes | 0.018 | 0.042 | 0.525 | [0.484, 0.564] |
| ste-descriptive.paragraph-without-related-information | no | 0.018 | 0.076 | 0.478 | [0.433, 0.525] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.002 | 0.009 | 0.486 | [0.442, 0.532] |
| ai-tells-register.over-formatting-reflex | no | 0.147 | 0.192 | 0.486 | [0.439, 0.537] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.221 | 0.254 | 0.510 | [0.460, 0.556] |
| ai-tells-structure.heading-echo | no | 0.166 | 0.241 | 0.510 | [0.463, 0.560] |
| ai-tells-content-shape.one-point-dilution | no | 0.239 | 0.282 | 0.509 | [0.463, 0.559] |
| ai-tells-structure.hollow-acknowledgment | no | 0.078 | 0.120 | 0.493 | [0.458, 0.528] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.002 | 0.008 | 0.494 | [0.451, 0.536] |
| ai-tells-structure.audience-straddle-remainder | no | 0.000 | 0.017 | 0.501 | [0.460, 0.542] |

## Per semantic rule, kev-9b-ft-s17

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.147 | 0.646 | 0.898 | [0.869, 0.925] |
| prose-discipline.marketing-register | no | 0.018 | 0.102 | 0.739 | [0.699, 0.782] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.007 | 0.018 | 0.705 | [0.662, 0.748] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.005 | 0.013 | 0.699 | [0.657, 0.739] |
| ste-sentences.sentence-not-short-or-clear | no | 0.051 | 0.129 | 0.686 | [0.644, 0.727] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.007 | 0.002 | 0.684 | [0.639, 0.738] |
| ai-tells-structure.analogy-stack-authority | no | 0.002 | 0.000 | 0.317 | [0.268, 0.364] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.007 | 0.005 | 0.664 | [0.619, 0.705] |
| ai-tells-structure.vague-attribution-remainder | no | 0.023 | 0.046 | 0.664 | [0.620, 0.706] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.000 | 0.008 | 0.347 | [0.298, 0.396] |
| ste-descriptive.missing-key-word-structure | no | 0.030 | 0.047 | 0.646 | [0.597, 0.695] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.007 | 0.001 | 0.357 | [0.316, 0.400] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.005 | 0.002 | 0.358 | [0.310, 0.404] |
| prose-discipline.hedged-into-uselessness | no | 0.018 | 0.022 | 0.634 | [0.587, 0.679] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.009 | 0.010 | 0.629 | [0.582, 0.680] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.016 | 0.042 | 0.628 | [0.588, 0.668] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.000 | 0.014 | 0.624 | [0.579, 0.666] |
| ai-tells-register.false-agency-remainder | no | 0.032 | 0.046 | 0.624 | [0.580, 0.670] |
| ai-tells-register.faux-candor-remainder | no | 0.002 | 0.003 | 0.620 | [0.572, 0.666] |
| ai-tells-register.hedged-symmetry | no | 0.009 | 0.018 | 0.617 | [0.577, 0.657] |
| ste-verbs.gerund-outside-noun-use | no | 0.023 | 0.036 | 0.611 | [0.563, 0.657] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.000 | 0.004 | 0.609 | [0.562, 0.660] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.001 | 0.599 | [0.552, 0.646] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.005 | 0.002 | 0.402 | [0.355, 0.457] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.009 | 0.018 | 0.589 | [0.546, 0.634] |
| ai-tells-register.organic-consequence-remainder | no | 0.021 | 0.031 | 0.589 | [0.547, 0.636] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.037 | 0.020 | 0.414 | [0.362, 0.463] |
| ai-tells-structure.heading-echo | no | 0.030 | 0.075 | 0.585 | [0.539, 0.638] |
| ai-tells-content-shape.one-point-dilution | no | 0.032 | 0.041 | 0.585 | [0.534, 0.637] |
| ai-tells-structure.invented-concept-label | yes | 0.000 | 0.001 | 0.416 | [0.366, 0.463] |
| ai-tells-structure.audience-straddle-remainder | no | 0.000 | 0.000 | 0.584 | [0.533, 0.633] |
| ai-tells-structure.hollow-acknowledgment | no | 0.014 | 0.014 | 0.579 | [0.539, 0.621] |
| ste-punctuation.parentheses-misuse | no | 0.007 | 0.010 | 0.578 | [0.534, 0.620] |
| ai-tells-content-shape.padded-symmetry | no | 0.009 | 0.003 | 0.575 | [0.523, 0.627] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.025 | 0.015 | 0.565 | [0.517, 0.613] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.010 | 0.446 | [0.395, 0.491] |
| ai-tells-structure.false-range | yes | 0.021 | 0.030 | 0.551 | [0.497, 0.602] |
| ai-tells-content-shape.elegant-variation | no | 0.025 | 0.054 | 0.549 | [0.504, 0.590] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.004 | 0.548 | [0.493, 0.601] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.003 | 0.542 | [0.490, 0.592] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.541 | [0.487, 0.595] |
| ste-descriptive.paragraph-without-related-information | no | 0.009 | 0.006 | 0.460 | [0.410, 0.512] |
| prose-discipline.overloaded-sentence | yes | 0.140 | 0.120 | 0.538 | [0.492, 0.587] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.002 | 0.524 | [0.472, 0.574] |
| ai-tells-structure.anaphora-abuse | no | 0.002 | 0.000 | 0.519 | [0.466, 0.573] |
| ai-tells-structure.false-suspense-remainder | no | 0.002 | 0.003 | 0.484 | [0.440, 0.529] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.002 | 0.003 | 0.485 | [0.436, 0.530] |
| ste-verbs.past-participle-not-adjectival | no | 0.048 | 0.061 | 0.515 | [0.468, 0.558] |
| ste-nouns.long-domain-term-without-short-form | no | 0.000 | 0.001 | 0.512 | [0.466, 0.555] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.028 | 0.023 | 0.510 | [0.461, 0.559] |
| ste-descriptive.information-not-gradual | yes | 0.000 | 0.003 | 0.508 | [0.462, 0.557] |
| ai-tells-content-shape.over-writing-remainder | no | 0.028 | 0.034 | 0.495 | [0.456, 0.536] |
| ai-tells-register.over-formatting-reflex | no | 0.044 | 0.078 | 0.504 | [0.455, 0.550] |
| ai-tells-structure.summary-closer-remainder | no | 0.000 | 0.004 | 0.497 | [0.444, 0.550] |
| ai-tells-structure.meta-narration-remainder | yes | 0.005 | 0.019 | 0.501 | [0.456, 0.545] |

## Per semantic rule, kev-9b-ft-s18

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.099 | 0.575 | 0.911 | [0.884, 0.937] |
| prose-discipline.marketing-register | no | 0.025 | 0.109 | 0.732 | [0.689, 0.774] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.002 | 0.007 | 0.731 | [0.686, 0.774] |
| ste-sentences.sentence-not-short-or-clear | no | 0.060 | 0.155 | 0.712 | [0.667, 0.753] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.005 | 0.013 | 0.697 | [0.654, 0.737] |
| ste-descriptive.missing-key-word-structure | no | 0.053 | 0.077 | 0.683 | [0.630, 0.733] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.009 | 0.019 | 0.676 | [0.632, 0.720] |
| ai-tells-structure.audience-straddle-remainder | no | 0.000 | 0.001 | 0.660 | [0.612, 0.706] |
| ste-nouns.long-domain-term-without-short-form | no | 0.000 | 0.000 | 0.656 | [0.609, 0.702] |
| ai-tells-register.organic-consequence-remainder | no | 0.030 | 0.067 | 0.653 | [0.610, 0.701] |
| ai-tells-structure.vague-attribution-remainder | no | 0.034 | 0.039 | 0.651 | [0.606, 0.693] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.005 | 0.009 | 0.650 | [0.609, 0.692] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.009 | 0.031 | 0.649 | [0.607, 0.692] |
| ste-verbs.gerund-outside-noun-use | no | 0.018 | 0.051 | 0.644 | [0.601, 0.686] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.002 | 0.007 | 0.634 | [0.590, 0.677] |
| ai-tells-register.faux-candor-remainder | no | 0.000 | 0.001 | 0.628 | [0.576, 0.678] |
| ai-tells-register.false-agency-remainder | no | 0.018 | 0.019 | 0.619 | [0.574, 0.666] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.005 | 0.002 | 0.613 | [0.567, 0.659] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.000 | 0.005 | 0.612 | [0.568, 0.655] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.037 | 0.029 | 0.609 | [0.558, 0.660] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.002 | 0.000 | 0.392 | [0.343, 0.439] |
| prose-discipline.hedged-into-uselessness | no | 0.002 | 0.010 | 0.606 | [0.563, 0.649] |
| ai-tells-content-shape.one-point-dilution | no | 0.021 | 0.027 | 0.598 | [0.548, 0.652] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.007 | 0.008 | 0.402 | [0.348, 0.458] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.011 | 0.003 | 0.406 | [0.359, 0.454] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.008 | 0.592 | [0.544, 0.639] |
| ai-tells-structure.heading-echo | no | 0.018 | 0.042 | 0.590 | [0.542, 0.643] |
| ai-tells-content-shape.elegant-variation | no | 0.005 | 0.015 | 0.589 | [0.542, 0.635] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.003 | 0.588 | [0.539, 0.634] |
| ai-tells-structure.false-range | yes | 0.021 | 0.059 | 0.587 | [0.542, 0.630] |
| ai-tells-structure.hollow-acknowledgment | no | 0.007 | 0.010 | 0.586 | [0.545, 0.627] |
| ai-tells-register.hedged-symmetry | no | 0.005 | 0.010 | 0.582 | [0.541, 0.623] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.000 | 0.002 | 0.582 | [0.532, 0.630] |
| prose-discipline.overloaded-sentence | yes | 0.154 | 0.137 | 0.577 | [0.529, 0.624] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.025 | 0.017 | 0.429 | [0.379, 0.483] |
| ste-descriptive.information-not-gradual | yes | 0.002 | 0.004 | 0.569 | [0.521, 0.618] |
| ai-tells-content-shape.padded-symmetry | no | 0.007 | 0.007 | 0.553 | [0.500, 0.604] |
| ste-descriptive.paragraph-without-related-information | no | 0.007 | 0.005 | 0.448 | [0.402, 0.500] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.009 | 0.002 | 0.457 | [0.404, 0.510] |
| ste-punctuation.parentheses-misuse | no | 0.005 | 0.002 | 0.536 | [0.485, 0.583] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.002 | 0.006 | 0.535 | [0.486, 0.585] |
| ai-tells-structure.analogy-stack-authority | no | 0.002 | 0.000 | 0.529 | [0.479, 0.581] |
| ste-verbs.past-participle-not-adjectival | no | 0.034 | 0.031 | 0.473 | [0.425, 0.520] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.018 | 0.016 | 0.475 | [0.426, 0.522] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.002 | 0.002 | 0.476 | [0.424, 0.526] |
| ai-tells-structure.anaphora-abuse | no | 0.002 | 0.001 | 0.476 | [0.428, 0.527] |
| prose-discipline.competing-actor-terms | no | 0.002 | 0.006 | 0.480 | [0.425, 0.530] |
| ai-tells-structure.false-suspense-remainder | no | 0.002 | 0.006 | 0.520 | [0.474, 0.565] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.002 | 0.518 | [0.467, 0.569] |
| ai-tells-content-shape.over-writing-remainder | no | 0.034 | 0.042 | 0.515 | [0.476, 0.555] |
| ai-tells-structure.summary-closer-remainder | no | 0.000 | 0.008 | 0.486 | [0.441, 0.532] |
| ai-tells-register.over-formatting-reflex | no | 0.025 | 0.077 | 0.514 | [0.464, 0.559] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.512 | [0.460, 0.561] |
| ai-tells-structure.invented-concept-label | yes | 0.000 | 0.002 | 0.490 | [0.440, 0.540] |
| ai-tells-structure.meta-narration-remainder | yes | 0.005 | 0.011 | 0.496 | [0.449, 0.541] |

## Per semantic rule, kev-9b-ft-s19

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.133 | 0.665 | 0.913 | [0.886, 0.940] |
| ste-sentences.sentence-not-short-or-clear | no | 0.025 | 0.092 | 0.734 | [0.692, 0.772] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.005 | 0.008 | 0.720 | [0.673, 0.764] |
| prose-discipline.marketing-register | no | 0.016 | 0.068 | 0.718 | [0.678, 0.764] |
| ste-nouns.long-domain-term-without-short-form | no | 0.000 | 0.006 | 0.685 | [0.641, 0.728] |
| ste-verbs.gerund-outside-noun-use | no | 0.016 | 0.029 | 0.678 | [0.632, 0.724] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.009 | 0.010 | 0.677 | [0.634, 0.720] |
| ai-tells-structure.vague-attribution-remainder | no | 0.023 | 0.029 | 0.666 | [0.623, 0.707] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.005 | 0.009 | 0.663 | [0.618, 0.706] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.000 | 0.661 | [0.614, 0.706] |
| prose-discipline.hedged-into-uselessness | no | 0.007 | 0.010 | 0.655 | [0.608, 0.702] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.005 | 0.002 | 0.654 | [0.604, 0.706] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.003 | 0.640 | [0.592, 0.687] |
| ai-tells-structure.audience-straddle-remainder | no | 0.000 | 0.000 | 0.640 | [0.594, 0.687] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.005 | 0.010 | 0.640 | [0.593, 0.688] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.000 | 0.002 | 0.638 | [0.591, 0.688] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.000 | 0.020 | 0.637 | [0.593, 0.677] |
| ste-descriptive.missing-key-word-structure | no | 0.018 | 0.019 | 0.635 | [0.578, 0.689] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.009 | 0.028 | 0.621 | [0.578, 0.664] |
| ai-tells-content-shape.elegant-variation | no | 0.009 | 0.028 | 0.621 | [0.577, 0.667] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.002 | 0.001 | 0.621 | [0.574, 0.670] |
| ai-tells-register.faux-candor-remainder | no | 0.000 | 0.002 | 0.613 | [0.563, 0.664] |
| ai-tells-register.organic-consequence-remainder | no | 0.009 | 0.025 | 0.611 | [0.562, 0.659] |
| ai-tells-register.hedged-symmetry | no | 0.011 | 0.016 | 0.605 | [0.559, 0.649] |
| ai-tells-register.false-agency-remainder | no | 0.039 | 0.023 | 0.597 | [0.556, 0.639] |
| ai-tells-structure.false-range | yes | 0.028 | 0.029 | 0.585 | [0.536, 0.634] |
| ai-tells-structure.hollow-acknowledgment | no | 0.018 | 0.013 | 0.580 | [0.538, 0.622] |
| ai-tells-content-shape.one-point-dilution | no | 0.030 | 0.036 | 0.577 | [0.528, 0.633] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.007 | 0.000 | 0.431 | [0.379, 0.488] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.007 | 0.005 | 0.439 | [0.384, 0.493] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.002 | 0.555 | [0.504, 0.603] |
| ai-tells-structure.invented-concept-label | yes | 0.002 | 0.003 | 0.554 | [0.499, 0.605] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.030 | 0.033 | 0.550 | [0.506, 0.601] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.002 | 0.010 | 0.452 | [0.399, 0.506] |
| ai-tells-structure.heading-echo | no | 0.064 | 0.114 | 0.548 | [0.500, 0.602] |
| ste-verbs.past-participle-not-adjectival | no | 0.071 | 0.098 | 0.548 | [0.501, 0.594] |
| ai-tells-content-shape.padded-symmetry | no | 0.016 | 0.007 | 0.544 | [0.495, 0.592] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.005 | 0.001 | 0.457 | [0.412, 0.502] |
| ste-descriptive.paragraph-without-related-information | no | 0.018 | 0.013 | 0.459 | [0.408, 0.512] |
| ai-tells-structure.meta-narration-remainder | yes | 0.018 | 0.040 | 0.540 | [0.497, 0.588] |
| prose-discipline.overloaded-sentence | yes | 0.083 | 0.061 | 0.538 | [0.488, 0.591] |
| ste-descriptive.information-not-gradual | yes | 0.000 | 0.002 | 0.534 | [0.487, 0.580] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.039 | 0.021 | 0.533 | [0.484, 0.581] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.055 | 0.025 | 0.473 | [0.423, 0.524] |
| ai-tells-register.over-formatting-reflex | no | 0.028 | 0.079 | 0.476 | [0.425, 0.523] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.010 | 0.523 | [0.472, 0.572] |
| ai-tells-structure.analogy-stack-authority | no | 0.002 | 0.000 | 0.522 | [0.471, 0.572] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.519 | [0.468, 0.570] |
| ai-tells-structure.summary-closer-remainder | no | 0.002 | 0.009 | 0.517 | [0.469, 0.564] |
| ai-tells-structure.false-suspense-remainder | no | 0.000 | 0.004 | 0.515 | [0.468, 0.562] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.005 | 0.004 | 0.513 | [0.459, 0.564] |
| ai-tells-structure.anaphora-abuse | no | 0.005 | 0.002 | 0.487 | [0.435, 0.542] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.003 | 0.492 | [0.442, 0.542] |
| ai-tells-content-shape.over-writing-remainder | no | 0.032 | 0.039 | 0.494 | [0.454, 0.533] |
| ste-punctuation.parentheses-misuse | no | 0.005 | 0.000 | 0.505 | [0.457, 0.554] |

## Per semantic rule, laya-english

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| prose-discipline.bare-quantifier-with-figure-available | no | 0.087 | 0.361 | 0.812 | [0.778, 0.848] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.110 | 0.419 | 0.799 | [0.762, 0.836] |
| ste-descriptive.paragraph-without-related-information | no | 0.384 | 0.670 | 0.787 | [0.749, 0.824] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.016 | 0.089 | 0.766 | [0.725, 0.804] |
| ai-tells-register.faux-candor-remainder | no | 0.414 | 0.708 | 0.761 | [0.721, 0.801] |
| ai-tells-structure.summary-closer-remainder | no | 0.064 | 0.270 | 0.758 | [0.721, 0.798] |
| ste-verbs.past-participle-not-adjectival | no | 0.085 | 0.257 | 0.757 | [0.716, 0.795] |
| ai-tells-structure.anaphora-abuse | no | 0.223 | 0.487 | 0.757 | [0.717, 0.796] |
| ai-tells-content-shape.over-writing-remainder | no | 0.582 | 0.808 | 0.757 | [0.716, 0.792] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.211 | 0.497 | 0.756 | [0.719, 0.794] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.377 | 0.646 | 0.756 | [0.714, 0.797] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.223 | 0.510 | 0.754 | [0.715, 0.792] |
| prose-discipline.competing-actor-terms | no | 0.264 | 0.552 | 0.750 | [0.708, 0.791] |
| ai-tells-structure.hollow-acknowledgment | no | 0.244 | 0.485 | 0.746 | [0.703, 0.786] |
| ai-tells-structure.analogy-stack-authority | no | 0.253 | 0.557 | 0.743 | [0.704, 0.784] |
| ai-tells-structure.vague-attribution-remainder | no | 0.041 | 0.215 | 0.742 | [0.701, 0.784] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.133 | 0.327 | 0.736 | [0.695, 0.778] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.494 | 0.710 | 0.729 | [0.688, 0.770] |
| ai-tells-register.over-formatting-reflex | no | 0.090 | 0.271 | 0.725 | [0.686, 0.765] |
| ai-tells-content-shape.padded-symmetry | no | 0.168 | 0.390 | 0.724 | [0.685, 0.762] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.034 | 0.160 | 0.723 | [0.679, 0.766] |
| ste-nouns.long-domain-term-without-short-form | no | 0.531 | 0.751 | 0.723 | [0.680, 0.761] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.267 | 0.504 | 0.723 | [0.681, 0.763] |
| prose-discipline.hedged-into-uselessness | no | 0.566 | 0.752 | 0.721 | [0.677, 0.761] |
| ai-tells-register.hedged-symmetry | no | 0.457 | 0.669 | 0.721 | [0.680, 0.761] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.278 | 0.503 | 0.718 | [0.675, 0.758] |
| prose-discipline.overloaded-sentence | yes | 0.437 | 0.657 | 0.717 | [0.673, 0.761] |
| ai-tells-structure.meta-narration-remainder | yes | 0.159 | 0.356 | 0.711 | [0.670, 0.752] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.179 | 0.406 | 0.710 | [0.670, 0.749] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.499 | 0.705 | 0.704 | [0.661, 0.746] |
| ste-verbs.gerund-outside-noun-use | no | 0.168 | 0.368 | 0.702 | [0.666, 0.739] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.216 | 0.427 | 0.693 | [0.650, 0.738] |
| ai-tells-structure.false-suspense-remainder | no | 0.651 | 0.808 | 0.692 | [0.652, 0.730] |
| ai-tells-register.false-agency-remainder | no | 0.241 | 0.398 | 0.683 | [0.640, 0.727] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.749 | 0.863 | 0.682 | [0.639, 0.724] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.389 | 0.587 | 0.676 | [0.629, 0.720] |
| ai-tells-structure.audience-straddle-remainder | no | 0.809 | 0.924 | 0.675 | [0.630, 0.716] |
| ste-punctuation.parentheses-misuse | no | 0.508 | 0.681 | 0.675 | [0.629, 0.722] |
| ste-descriptive.missing-key-word-structure | no | 0.120 | 0.285 | 0.673 | [0.629, 0.715] |
| ai-tells-content-shape.one-point-dilution | no | 0.632 | 0.757 | 0.673 | [0.628, 0.721] |
| orwell.concrete-floor | no | 0.644 | 0.768 | 0.672 | [0.626, 0.715] |
| ste-practices.ambiguous-preposition-with | no | 0.405 | 0.581 | 0.670 | [0.625, 0.716] |
| ai-tells-structure.invented-concept-label | yes | 0.669 | 0.783 | 0.668 | [0.621, 0.712] |
| ai-tells-structure.heading-echo | no | 0.166 | 0.273 | 0.659 | [0.616, 0.704] |
| ste-sentences.sentence-not-short-or-clear | no | 0.731 | 0.826 | 0.656 | [0.614, 0.700] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.667 | 0.796 | 0.642 | [0.597, 0.684] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.913 | 0.954 | 0.632 | [0.581, 0.678] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.632 | 0.746 | 0.632 | [0.584, 0.678] |
| prose-discipline.marketing-register | no | 0.795 | 0.860 | 0.620 | [0.576, 0.667] |
| ste-descriptive.information-not-gradual | yes | 0.692 | 0.800 | 0.617 | [0.567, 0.662] |
| ai-tells-structure.false-range | yes | 0.200 | 0.327 | 0.613 | [0.568, 0.659] |
| ai-tells-register.organic-consequence-remainder | no | 0.789 | 0.863 | 0.606 | [0.559, 0.651] |
| ai-tells-content-shape.elegant-variation | no | 0.887 | 0.928 | 0.569 | [0.519, 0.619] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.823 | 0.874 | 0.540 | [0.490, 0.590] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.710 | 0.764 | 0.528 | [0.480, 0.575] |

## Per semantic rule, laya-multilingual

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| ste-safety.risk-level-word-missing-or-wrong | no | 0.623 | 0.821 | 0.630 | [0.584, 0.675] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.614 | 0.782 | 0.622 | [0.579, 0.668] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.508 | 0.660 | 0.617 | [0.570, 0.665] |
| ai-tells-structure.anaphora-abuse | no | 0.611 | 0.757 | 0.616 | [0.570, 0.658] |
| ai-tells-register.false-agency-remainder | no | 0.310 | 0.434 | 0.609 | [0.563, 0.658] |
| prose-discipline.competing-actor-terms | no | 0.782 | 0.879 | 0.607 | [0.557, 0.655] |
| prose-discipline.hedged-into-uselessness | no | 0.641 | 0.778 | 0.600 | [0.552, 0.647] |
| ai-tells-structure.false-range | yes | 0.680 | 0.776 | 0.597 | [0.546, 0.647] |
| ai-tells-structure.meta-narration-remainder | yes | 0.669 | 0.815 | 0.596 | [0.551, 0.641] |
| ai-tells-structure.hollow-acknowledgment | no | 0.586 | 0.716 | 0.595 | [0.555, 0.637] |
| ste-descriptive.paragraph-without-related-information | no | 0.740 | 0.824 | 0.592 | [0.547, 0.638] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.703 | 0.814 | 0.590 | [0.544, 0.634] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.455 | 0.592 | 0.589 | [0.545, 0.633] |
| ste-punctuation.parentheses-misuse | no | 0.637 | 0.737 | 0.585 | [0.541, 0.628] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.630 | 0.740 | 0.585 | [0.540, 0.631] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.644 | 0.743 | 0.584 | [0.541, 0.633] |
| ai-tells-structure.analogy-stack-authority | no | 0.469 | 0.570 | 0.583 | [0.541, 0.626] |
| ste-descriptive.missing-key-word-structure | no | 0.480 | 0.627 | 0.582 | [0.542, 0.623] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.701 | 0.812 | 0.577 | [0.529, 0.623] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.706 | 0.821 | 0.576 | [0.531, 0.623] |
| ai-tells-register.faux-candor-remainder | no | 0.324 | 0.398 | 0.570 | [0.526, 0.618] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.786 | 0.863 | 0.569 | [0.523, 0.615] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.793 | 0.846 | 0.569 | [0.522, 0.617] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.699 | 0.795 | 0.566 | [0.517, 0.614] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.676 | 0.754 | 0.565 | [0.520, 0.610] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.759 | 0.827 | 0.565 | [0.513, 0.612] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.775 | 0.844 | 0.563 | [0.516, 0.608] |
| ai-tells-register.hedged-symmetry | no | 0.671 | 0.773 | 0.562 | [0.518, 0.607] |
| ai-tells-content-shape.padded-symmetry | no | 0.798 | 0.846 | 0.560 | [0.511, 0.608] |
| orwell.concrete-floor | no | 0.506 | 0.616 | 0.559 | [0.515, 0.604] |
| ste-descriptive.information-not-gradual | yes | 0.749 | 0.834 | 0.558 | [0.514, 0.604] |
| ste-sentences.sentence-not-short-or-clear | no | 0.830 | 0.880 | 0.558 | [0.507, 0.608] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.697 | 0.789 | 0.557 | [0.512, 0.604] |
| ai-tells-structure.vague-attribution-remainder | no | 0.515 | 0.568 | 0.557 | [0.512, 0.605] |
| ai-tells-structure.false-suspense-remainder | no | 0.540 | 0.645 | 0.555 | [0.513, 0.597] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.600 | 0.695 | 0.555 | [0.508, 0.603] |
| ai-tells-content-shape.one-point-dilution | no | 0.648 | 0.742 | 0.555 | [0.512, 0.600] |
| ai-tells-structure.summary-closer-remainder | no | 0.802 | 0.861 | 0.552 | [0.505, 0.606] |
| ai-tells-register.over-formatting-reflex | no | 0.784 | 0.824 | 0.552 | [0.504, 0.600] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.736 | 0.808 | 0.550 | [0.502, 0.600] |
| ste-practices.ambiguous-preposition-with | no | 0.703 | 0.763 | 0.550 | [0.504, 0.596] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.674 | 0.759 | 0.548 | [0.505, 0.595] |
| ste-nouns.long-domain-term-without-short-form | no | 0.766 | 0.868 | 0.544 | [0.498, 0.588] |
| prose-discipline.marketing-register | no | 0.214 | 0.229 | 0.543 | [0.495, 0.594] |
| ai-tells-content-shape.elegant-variation | no | 0.913 | 0.945 | 0.537 | [0.486, 0.586] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.717 | 0.780 | 0.529 | [0.481, 0.574] |
| prose-discipline.overloaded-sentence | yes | 0.777 | 0.842 | 0.528 | [0.478, 0.577] |
| ai-tells-content-shape.over-writing-remainder | no | 0.651 | 0.698 | 0.527 | [0.482, 0.576] |
| ste-verbs.gerund-outside-noun-use | no | 0.851 | 0.886 | 0.519 | [0.470, 0.565] |
| ai-tells-structure.audience-straddle-remainder | no | 0.920 | 0.940 | 0.516 | [0.463, 0.576] |
| ste-verbs.past-participle-not-adjectival | no | 0.513 | 0.542 | 0.490 | [0.446, 0.535] |
| ai-tells-structure.heading-echo | no | 0.920 | 0.938 | 0.492 | [0.439, 0.540] |
| ai-tells-register.organic-consequence-remainder | no | 0.798 | 0.817 | 0.494 | [0.447, 0.545] |
| ai-tells-structure.invented-concept-label | yes | 0.602 | 0.640 | 0.501 | [0.456, 0.547] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.917 | 0.914 | 0.500 | [0.449, 0.548] |

## Per semantic rule, laya-typed-decisions

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| ai-tells-structure.absolute-assertion-remainder | no | 0.021 | 0.076 | 0.735 | [0.698, 0.773] |
| ai-tells-content-shape.over-writing-remainder | no | 0.722 | 0.892 | 0.707 | [0.669, 0.745] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.485 | 0.724 | 0.699 | [0.655, 0.740] |
| ai-tells-register.faux-candor-remainder | no | 0.370 | 0.628 | 0.698 | [0.653, 0.741] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.232 | 0.453 | 0.692 | [0.649, 0.734] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.402 | 0.647 | 0.688 | [0.645, 0.729] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.193 | 0.419 | 0.678 | [0.637, 0.718] |
| prose-discipline.competing-actor-terms | no | 0.294 | 0.535 | 0.678 | [0.638, 0.719] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.149 | 0.302 | 0.674 | [0.634, 0.715] |
| ste-descriptive.paragraph-without-related-information | no | 0.492 | 0.703 | 0.671 | [0.628, 0.714] |
| ai-tells-structure.analogy-stack-authority | no | 0.248 | 0.467 | 0.669 | [0.629, 0.705] |
| ai-tells-structure.vague-attribution-remainder | no | 0.324 | 0.568 | 0.663 | [0.624, 0.702] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.124 | 0.269 | 0.660 | [0.613, 0.704] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.299 | 0.513 | 0.652 | [0.612, 0.691] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.384 | 0.568 | 0.647 | [0.604, 0.688] |
| ste-nouns.long-domain-term-without-short-form | no | 0.476 | 0.688 | 0.645 | [0.603, 0.683] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.131 | 0.256 | 0.642 | [0.599, 0.686] |
| prose-discipline.overloaded-sentence | yes | 0.398 | 0.597 | 0.640 | [0.598, 0.682] |
| ste-verbs.past-participle-not-adjectival | no | 0.129 | 0.243 | 0.638 | [0.594, 0.678] |
| ai-tells-structure.anaphora-abuse | no | 0.287 | 0.449 | 0.636 | [0.595, 0.674] |
| ai-tells-structure.summary-closer-remainder | no | 0.117 | 0.206 | 0.627 | [0.586, 0.668] |
| ste-verbs.gerund-outside-noun-use | no | 0.368 | 0.541 | 0.626 | [0.585, 0.667] |
| ai-tells-structure.false-range | yes | 0.264 | 0.429 | 0.626 | [0.585, 0.665] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.255 | 0.428 | 0.625 | [0.585, 0.664] |
| ai-tells-register.false-agency-remainder | no | 0.223 | 0.368 | 0.621 | [0.578, 0.666] |
| ai-tells-register.hedged-symmetry | no | 0.368 | 0.527 | 0.619 | [0.578, 0.661] |
| ai-tells-content-shape.elegant-variation | no | 0.474 | 0.621 | 0.618 | [0.576, 0.662] |
| prose-discipline.hedged-into-uselessness | no | 0.303 | 0.465 | 0.616 | [0.573, 0.658] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.338 | 0.520 | 0.615 | [0.573, 0.656] |
| ai-tells-structure.audience-straddle-remainder | no | 0.736 | 0.855 | 0.615 | [0.574, 0.658] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.699 | 0.799 | 0.614 | [0.568, 0.657] |
| orwell.concrete-floor | no | 0.545 | 0.749 | 0.612 | [0.571, 0.651] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.676 | 0.809 | 0.607 | [0.566, 0.647] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.343 | 0.497 | 0.606 | [0.561, 0.651] |
| ai-tells-structure.hollow-acknowledgment | no | 0.184 | 0.276 | 0.602 | [0.561, 0.641] |
| ai-tells-structure.heading-echo | no | 0.322 | 0.442 | 0.600 | [0.559, 0.641] |
| ste-practices.ambiguous-preposition-with | no | 0.329 | 0.447 | 0.596 | [0.554, 0.638] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.310 | 0.450 | 0.596 | [0.549, 0.640] |
| ai-tells-register.over-formatting-reflex | no | 0.207 | 0.248 | 0.591 | [0.549, 0.634] |
| ai-tells-content-shape.padded-symmetry | no | 0.108 | 0.175 | 0.589 | [0.549, 0.628] |
| prose-discipline.marketing-register | no | 0.660 | 0.750 | 0.587 | [0.542, 0.629] |
| ste-descriptive.information-not-gradual | yes | 0.579 | 0.669 | 0.584 | [0.540, 0.627] |
| ste-punctuation.parentheses-misuse | no | 0.280 | 0.391 | 0.583 | [0.540, 0.624] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.572 | 0.658 | 0.579 | [0.533, 0.623] |
| ai-tells-register.organic-consequence-remainder | no | 0.653 | 0.742 | 0.574 | [0.532, 0.616] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.161 | 0.203 | 0.574 | [0.530, 0.616] |
| ai-tells-content-shape.one-point-dilution | no | 0.520 | 0.577 | 0.572 | [0.525, 0.618] |
| ai-tells-structure.meta-narration-remainder | yes | 0.232 | 0.339 | 0.568 | [0.527, 0.610] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.480 | 0.552 | 0.564 | [0.518, 0.612] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.149 | 0.153 | 0.438 | [0.398, 0.481] |
| ste-descriptive.missing-key-word-structure | no | 0.115 | 0.179 | 0.558 | [0.513, 0.600] |
| ai-tells-structure.invented-concept-label | yes | 0.430 | 0.480 | 0.557 | [0.510, 0.602] |
| ste-sentences.sentence-not-short-or-clear | no | 0.308 | 0.419 | 0.555 | [0.512, 0.598] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.389 | 0.456 | 0.553 | [0.509, 0.596] |
| ai-tells-structure.false-suspense-remainder | no | 0.577 | 0.584 | 0.514 | [0.466, 0.558] |

## Per semantic rule, v3-kev-0.8b-ft-s17

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| ai-tells-structure.audience-straddle-remainder | no | 0.071 | 0.020 | 0.277 | [0.240, 0.319] |
| ste-descriptive.information-not-gradual | yes | 0.048 | 0.148 | 0.679 | [0.635, 0.718] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.060 | 0.089 | 0.674 | [0.622, 0.721] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.007 | 0.003 | 0.334 | [0.295, 0.377] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.016 | 0.003 | 0.343 | [0.303, 0.385] |
| ai-tells-register.organic-consequence-remainder | no | 0.053 | 0.018 | 0.359 | [0.318, 0.399] |
| ai-tells-structure.vague-attribution-remainder | no | 0.009 | 0.003 | 0.639 | [0.585, 0.690] |
| prose-discipline.overloaded-sentence | yes | 0.005 | 0.010 | 0.635 | [0.595, 0.678] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.034 | 0.035 | 0.625 | [0.577, 0.673] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.023 | 0.008 | 0.384 | [0.341, 0.428] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.057 | 0.011 | 0.389 | [0.345, 0.437] |
| ai-tells-structure.summary-closer-remainder | no | 0.007 | 0.002 | 0.395 | [0.349, 0.441] |
| ai-tells-structure.analogy-stack-authority | no | 0.000 | 0.000 | 0.397 | [0.351, 0.444] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.005 | 0.006 | 0.400 | [0.358, 0.443] |
| ai-tells-structure.false-range | yes | 0.009 | 0.003 | 0.408 | [0.364, 0.456] |
| ai-tells-register.hedged-symmetry | no | 0.005 | 0.002 | 0.416 | [0.371, 0.464] |
| ai-tells-content-shape.over-writing-remainder | no | 0.009 | 0.002 | 0.417 | [0.375, 0.463] |
| ste-nouns.long-domain-term-without-short-form | no | 0.028 | 0.016 | 0.417 | [0.375, 0.457] |
| ste-punctuation.parentheses-misuse | no | 0.067 | 0.074 | 0.581 | [0.539, 0.622] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.000 | 0.422 | [0.380, 0.467] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.016 | 0.036 | 0.573 | [0.524, 0.617] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.007 | 0.000 | 0.429 | [0.384, 0.479] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.002 | 0.000 | 0.429 | [0.386, 0.476] |
| ai-tells-register.faux-candor-remainder | no | 0.030 | 0.018 | 0.431 | [0.389, 0.480] |
| ai-tells-content-shape.padded-symmetry | no | 0.018 | 0.011 | 0.433 | [0.385, 0.478] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.009 | 0.000 | 0.439 | [0.397, 0.485] |
| prose-discipline.marketing-register | no | 0.000 | 0.002 | 0.561 | [0.508, 0.611] |
| ai-tells-register.false-agency-remainder | no | 0.007 | 0.007 | 0.559 | [0.511, 0.607] |
| ste-verbs.gerund-outside-noun-use | no | 0.018 | 0.039 | 0.559 | [0.518, 0.599] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.030 | 0.013 | 0.442 | [0.400, 0.487] |
| ai-tells-content-shape.one-point-dilution | no | 0.000 | 0.003 | 0.445 | [0.403, 0.489] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.023 | 0.021 | 0.553 | [0.507, 0.597] |
| ste-verbs.past-participle-not-adjectival | no | 0.023 | 0.027 | 0.551 | [0.511, 0.595] |
| ai-tells-structure.meta-narration-remainder | yes | 0.030 | 0.020 | 0.450 | [0.403, 0.496] |
| ai-tells-content-shape.elegant-variation | no | 0.087 | 0.050 | 0.450 | [0.407, 0.493] |
| ai-tells-structure.anaphora-abuse | no | 0.034 | 0.049 | 0.454 | [0.409, 0.500] |
| ste-descriptive.missing-key-word-structure | no | 0.005 | 0.009 | 0.455 | [0.411, 0.498] |
| orwell.concrete-floor | no | 0.002 | 0.006 | 0.545 | [0.501, 0.582] |
| ste-sentences.sentence-not-short-or-clear | no | 0.048 | 0.062 | 0.542 | [0.497, 0.585] |
| ai-tells-structure.invented-concept-label | yes | 0.023 | 0.020 | 0.538 | [0.495, 0.580] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.005 | 0.003 | 0.466 | [0.426, 0.508] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.057 | 0.033 | 0.533 | [0.483, 0.583] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.014 | 0.041 | 0.533 | [0.489, 0.582] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.000 | 0.002 | 0.468 | [0.431, 0.508] |
| ai-tells-structure.false-suspense-remainder | no | 0.023 | 0.031 | 0.531 | [0.480, 0.579] |
| ai-tells-structure.heading-echo | no | 0.034 | 0.055 | 0.471 | [0.421, 0.519] |
| ste-practices.ambiguous-preposition-with | no | 0.023 | 0.057 | 0.526 | [0.484, 0.571] |
| ai-tells-register.over-formatting-reflex | no | 0.023 | 0.019 | 0.474 | [0.428, 0.518] |
| ste-descriptive.paragraph-without-related-information | no | 0.060 | 0.031 | 0.475 | [0.429, 0.519] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.014 | 0.004 | 0.524 | [0.478, 0.574] |
| prose-discipline.hedged-into-uselessness | no | 0.023 | 0.045 | 0.491 | [0.444, 0.534] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.055 | 0.036 | 0.507 | [0.466, 0.549] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.002 | 0.003 | 0.493 | [0.447, 0.538] |
| ai-tells-structure.hollow-acknowledgment | no | 0.005 | 0.004 | 0.495 | [0.448, 0.539] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.005 | 0.003 | 0.495 | [0.444, 0.540] |

## Per semantic rule, v3-kev-0.8b-ft-s18

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| ai-tells-structure.negative-inventory-remainder | yes | 0.000 | 0.002 | 0.300 | [0.265, 0.336] |
| ai-tells-register.organic-consequence-remainder | no | 0.034 | 0.010 | 0.319 | [0.278, 0.359] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.005 | 0.002 | 0.329 | [0.288, 0.368] |
| ai-tells-structure.audience-straddle-remainder | no | 0.046 | 0.010 | 0.331 | [0.287, 0.374] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.048 | 0.018 | 0.339 | [0.298, 0.382] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.028 | 0.049 | 0.645 | [0.596, 0.695] |
| ste-descriptive.paragraph-without-related-information | no | 0.005 | 0.002 | 0.367 | [0.326, 0.407] |
| ai-tells-structure.false-range | yes | 0.000 | 0.001 | 0.368 | [0.323, 0.416] |
| ai-tells-structure.meta-narration-remainder | yes | 0.007 | 0.006 | 0.375 | [0.336, 0.415] |
| ste-verbs.gerund-outside-noun-use | no | 0.014 | 0.036 | 0.624 | [0.586, 0.664] |
| ste-descriptive.information-not-gradual | yes | 0.007 | 0.023 | 0.621 | [0.572, 0.666] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.002 | 0.000 | 0.385 | [0.343, 0.427] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.009 | 0.007 | 0.388 | [0.344, 0.438] |
| ai-tells-structure.analogy-stack-authority | no | 0.005 | 0.001 | 0.392 | [0.348, 0.440] |
| orwell.concrete-floor | no | 0.000 | 0.013 | 0.604 | [0.565, 0.641] |
| ai-tells-content-shape.over-writing-remainder | no | 0.000 | 0.000 | 0.398 | [0.355, 0.443] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.014 | 0.002 | 0.600 | [0.558, 0.645] |
| ste-nouns.long-domain-term-without-short-form | no | 0.009 | 0.000 | 0.401 | [0.359, 0.448] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.002 | 0.000 | 0.403 | [0.359, 0.451] |
| ste-descriptive.missing-key-word-structure | no | 0.007 | 0.005 | 0.405 | [0.362, 0.453] |
| ai-tells-content-shape.padded-symmetry | no | 0.002 | 0.000 | 0.411 | [0.367, 0.452] |
| ai-tells-register.over-formatting-reflex | no | 0.030 | 0.075 | 0.588 | [0.539, 0.635] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.002 | 0.003 | 0.416 | [0.375, 0.460] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.005 | 0.004 | 0.582 | [0.535, 0.632] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.002 | 0.003 | 0.421 | [0.378, 0.464] |
| ai-tells-structure.vague-attribution-remainder | no | 0.011 | 0.005 | 0.578 | [0.529, 0.626] |
| ai-tells-structure.summary-closer-remainder | no | 0.002 | 0.000 | 0.423 | [0.373, 0.470] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.002 | 0.001 | 0.425 | [0.384, 0.468] |
| prose-discipline.marketing-register | no | 0.000 | 0.002 | 0.426 | [0.378, 0.476] |
| ai-tells-structure.heading-echo | no | 0.094 | 0.166 | 0.573 | [0.531, 0.619] |
| ai-tells-register.hedged-symmetry | no | 0.009 | 0.001 | 0.434 | [0.393, 0.475] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.041 | 0.003 | 0.435 | [0.389, 0.484] |
| ai-tells-content-shape.one-point-dilution | no | 0.000 | 0.003 | 0.439 | [0.399, 0.482] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.014 | 0.021 | 0.554 | [0.511, 0.599] |
| ste-practices.ambiguous-preposition-with | no | 0.014 | 0.009 | 0.449 | [0.407, 0.488] |
| ste-sentences.sentence-not-short-or-clear | no | 0.011 | 0.021 | 0.549 | [0.505, 0.592] |
| ste-verbs.past-participle-not-adjectival | no | 0.032 | 0.028 | 0.546 | [0.509, 0.583] |
| prose-discipline.hedged-into-uselessness | no | 0.002 | 0.007 | 0.457 | [0.410, 0.502] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.014 | 0.023 | 0.540 | [0.492, 0.590] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.000 | 0.460 | [0.417, 0.501] |
| ai-tells-content-shape.elegant-variation | no | 0.007 | 0.003 | 0.461 | [0.418, 0.504] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.000 | 0.463 | [0.422, 0.507] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.002 | 0.002 | 0.464 | [0.427, 0.498] |
| ai-tells-structure.false-suspense-remainder | no | 0.046 | 0.033 | 0.535 | [0.488, 0.582] |
| ai-tells-structure.anaphora-abuse | no | 0.007 | 0.005 | 0.465 | [0.429, 0.509] |
| ste-punctuation.parentheses-misuse | no | 0.011 | 0.009 | 0.467 | [0.424, 0.510] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.000 | 0.000 | 0.467 | [0.419, 0.515] |
| ai-tells-register.faux-candor-remainder | no | 0.009 | 0.021 | 0.471 | [0.426, 0.517] |
| ai-tells-structure.hollow-acknowledgment | no | 0.011 | 0.010 | 0.472 | [0.433, 0.513] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.009 | 0.002 | 0.523 | [0.484, 0.564] |
| ai-tells-structure.invented-concept-label | yes | 0.005 | 0.003 | 0.478 | [0.435, 0.522] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.039 | 0.018 | 0.484 | [0.444, 0.525] |
| ai-tells-register.false-agency-remainder | no | 0.005 | 0.005 | 0.515 | [0.470, 0.556] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.009 | 0.009 | 0.511 | [0.472, 0.550] |
| prose-discipline.overloaded-sentence | yes | 0.000 | 0.000 | 0.502 | [0.458, 0.549] |

## Per semantic rule, v3-kev-0.8b-ft-s19

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.055 | 0.016 | 0.265 | [0.224, 0.304] |
| ai-tells-structure.false-range | yes | 0.002 | 0.002 | 0.290 | [0.249, 0.332] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.005 | 0.003 | 0.318 | [0.278, 0.356] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.000 | 0.002 | 0.324 | [0.285, 0.367] |
| ai-tells-register.organic-consequence-remainder | no | 0.060 | 0.020 | 0.327 | [0.289, 0.365] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.023 | 0.057 | 0.671 | [0.624, 0.717] |
| ai-tells-content-shape.over-writing-remainder | no | 0.002 | 0.001 | 0.332 | [0.295, 0.372] |
| ai-tells-structure.audience-straddle-remainder | no | 0.030 | 0.008 | 0.344 | [0.307, 0.381] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.009 | 0.003 | 0.361 | [0.320, 0.405] |
| ai-tells-structure.analogy-stack-authority | no | 0.000 | 0.001 | 0.364 | [0.319, 0.414] |
| ste-descriptive.paragraph-without-related-information | no | 0.009 | 0.003 | 0.367 | [0.325, 0.409] |
| prose-discipline.marketing-register | no | 0.002 | 0.003 | 0.375 | [0.328, 0.420] |
| ai-tells-content-shape.padded-symmetry | no | 0.023 | 0.010 | 0.376 | [0.336, 0.420] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.007 | 0.000 | 0.376 | [0.334, 0.419] |
| ai-tells-register.hedged-symmetry | no | 0.002 | 0.004 | 0.388 | [0.347, 0.431] |
| ai-tells-content-shape.elegant-variation | no | 0.002 | 0.007 | 0.390 | [0.344, 0.436] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.001 | 0.396 | [0.354, 0.440] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.002 | 0.011 | 0.404 | [0.360, 0.453] |
| ai-tells-structure.summary-closer-remainder | no | 0.000 | 0.000 | 0.404 | [0.362, 0.449] |
| ste-punctuation.parentheses-misuse | no | 0.011 | 0.008 | 0.406 | [0.361, 0.453] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.002 | 0.003 | 0.409 | [0.367, 0.452] |
| ai-tells-structure.anaphora-abuse | no | 0.014 | 0.017 | 0.410 | [0.366, 0.456] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.000 | 0.412 | [0.372, 0.456] |
| ste-practices.ambiguous-preposition-with | no | 0.011 | 0.014 | 0.413 | [0.372, 0.454] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.000 | 0.000 | 0.418 | [0.369, 0.465] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.011 | 0.003 | 0.418 | [0.379, 0.466] |
| ste-nouns.long-domain-term-without-short-form | no | 0.028 | 0.012 | 0.422 | [0.378, 0.467] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.025 | 0.001 | 0.422 | [0.377, 0.467] |
| ste-descriptive.information-not-gradual | yes | 0.014 | 0.060 | 0.577 | [0.532, 0.619] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.009 | 0.000 | 0.564 | [0.517, 0.607] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.009 | 0.005 | 0.436 | [0.395, 0.481] |
| ai-tells-structure.meta-narration-remainder | yes | 0.025 | 0.029 | 0.436 | [0.392, 0.481] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.007 | 0.003 | 0.440 | [0.404, 0.478] |
| ai-tells-structure.heading-echo | no | 0.030 | 0.063 | 0.557 | [0.513, 0.610] |
| ste-verbs.gerund-outside-noun-use | no | 0.067 | 0.093 | 0.553 | [0.515, 0.595] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.002 | 0.001 | 0.447 | [0.403, 0.495] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.014 | 0.043 | 0.553 | [0.511, 0.598] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.087 | 0.048 | 0.449 | [0.412, 0.487] |
| ste-descriptive.missing-key-word-structure | no | 0.005 | 0.014 | 0.459 | [0.413, 0.509] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.000 | 0.464 | [0.421, 0.508] |
| ai-tells-structure.vague-attribution-remainder | no | 0.014 | 0.009 | 0.530 | [0.482, 0.579] |
| ai-tells-register.faux-candor-remainder | no | 0.016 | 0.016 | 0.471 | [0.429, 0.514] |
| ste-sentences.sentence-not-short-or-clear | no | 0.016 | 0.036 | 0.528 | [0.486, 0.569] |
| prose-discipline.hedged-into-uselessness | no | 0.000 | 0.004 | 0.474 | [0.429, 0.518] |
| ai-tells-content-shape.one-point-dilution | no | 0.000 | 0.006 | 0.475 | [0.429, 0.519] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.023 | 0.048 | 0.523 | [0.477, 0.572] |
| orwell.concrete-floor | no | 0.000 | 0.004 | 0.523 | [0.480, 0.564] |
| ai-tells-register.over-formatting-reflex | no | 0.028 | 0.028 | 0.486 | [0.445, 0.527] |
| ste-verbs.past-participle-not-adjectival | no | 0.034 | 0.045 | 0.513 | [0.474, 0.554] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.023 | 0.010 | 0.512 | [0.465, 0.557] |
| ai-tells-structure.false-suspense-remainder | no | 0.046 | 0.055 | 0.510 | [0.464, 0.556] |
| prose-discipline.overloaded-sentence | yes | 0.000 | 0.001 | 0.509 | [0.464, 0.555] |
| ai-tells-structure.invented-concept-label | yes | 0.007 | 0.008 | 0.495 | [0.448, 0.540] |
| ai-tells-register.false-agency-remainder | no | 0.007 | 0.003 | 0.497 | [0.447, 0.543] |
| ai-tells-structure.hollow-acknowledgment | no | 0.023 | 0.037 | 0.498 | [0.453, 0.540] |

## Per semantic rule, v3-kev-4b-ft-s17

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.018 | 0.221 | 0.866 | [0.832, 0.896] |
| ai-tells-structure.summary-closer-remainder | no | 0.002 | 0.042 | 0.801 | [0.764, 0.835] |
| ste-nouns.long-domain-term-without-short-form | no | 0.000 | 0.016 | 0.750 | [0.706, 0.793] |
| ste-verbs.gerund-outside-noun-use | no | 0.097 | 0.258 | 0.743 | [0.703, 0.784] |
| ai-tells-content-shape.one-point-dilution | no | 0.000 | 0.036 | 0.740 | [0.698, 0.782] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.000 | 0.004 | 0.720 | [0.676, 0.759] |
| prose-discipline.overloaded-sentence | yes | 0.037 | 0.153 | 0.716 | [0.674, 0.754] |
| ste-descriptive.missing-key-word-structure | no | 0.000 | 0.000 | 0.714 | [0.665, 0.758] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.000 | 0.002 | 0.712 | [0.666, 0.757] |
| prose-discipline.marketing-register | no | 0.002 | 0.026 | 0.705 | [0.666, 0.745] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.002 | 0.004 | 0.697 | [0.654, 0.737] |
| ste-sentences.sentence-not-short-or-clear | no | 0.000 | 0.029 | 0.696 | [0.655, 0.732] |
| ste-descriptive.paragraph-without-related-information | no | 0.002 | 0.003 | 0.688 | [0.642, 0.735] |
| ai-tells-structure.heading-echo | no | 0.051 | 0.156 | 0.672 | [0.630, 0.717] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.005 | 0.024 | 0.672 | [0.628, 0.712] |
| ai-tells-structure.audience-straddle-remainder | no | 0.000 | 0.000 | 0.671 | [0.626, 0.713] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.000 | 0.651 | [0.605, 0.696] |
| ste-descriptive.information-not-gradual | yes | 0.000 | 0.001 | 0.637 | [0.586, 0.684] |
| ai-tells-content-shape.over-writing-remainder | no | 0.014 | 0.011 | 0.633 | [0.590, 0.673] |
| ai-tells-structure.vague-attribution-remainder | no | 0.009 | 0.003 | 0.627 | [0.578, 0.674] |
| ai-tells-content-shape.padded-symmetry | no | 0.000 | 0.003 | 0.623 | [0.581, 0.668] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.009 | 0.010 | 0.611 | [0.563, 0.658] |
| prose-discipline.hedged-into-uselessness | no | 0.002 | 0.011 | 0.604 | [0.557, 0.646] |
| ai-tells-register.over-formatting-reflex | no | 0.002 | 0.023 | 0.599 | [0.551, 0.649] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.006 | 0.597 | [0.550, 0.643] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.014 | 0.013 | 0.592 | [0.541, 0.641] |
| ai-tells-structure.false-range | yes | 0.002 | 0.000 | 0.412 | [0.360, 0.461] |
| ai-tells-structure.hollow-acknowledgment | no | 0.007 | 0.019 | 0.588 | [0.547, 0.627] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.000 | 0.585 | [0.534, 0.628] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.004 | 0.584 | [0.534, 0.632] |
| ai-tells-structure.invented-concept-label | yes | 0.007 | 0.002 | 0.583 | [0.535, 0.635] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.000 | 0.001 | 0.582 | [0.537, 0.627] |
| ai-tells-structure.meta-narration-remainder | yes | 0.021 | 0.030 | 0.579 | [0.536, 0.625] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.002 | 0.001 | 0.579 | [0.531, 0.624] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.011 | 0.004 | 0.578 | [0.535, 0.617] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.000 | 0.002 | 0.570 | [0.526, 0.610] |
| ste-punctuation.parentheses-misuse | no | 0.016 | 0.012 | 0.570 | [0.525, 0.614] |
| ai-tells-register.false-agency-remainder | no | 0.007 | 0.012 | 0.569 | [0.530, 0.608] |
| ai-tells-register.faux-candor-remainder | no | 0.000 | 0.001 | 0.559 | [0.514, 0.605] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.000 | 0.000 | 0.554 | [0.507, 0.603] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.005 | 0.011 | 0.450 | [0.402, 0.496] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.001 | 0.451 | [0.398, 0.499] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.000 | 0.002 | 0.546 | [0.497, 0.595] |
| ai-tells-structure.analogy-stack-authority | no | 0.000 | 0.001 | 0.546 | [0.504, 0.596] |
| ai-tells-register.organic-consequence-remainder | no | 0.000 | 0.003 | 0.454 | [0.411, 0.505] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.016 | 0.034 | 0.542 | [0.495, 0.588] |
| ai-tells-structure.anaphora-abuse | no | 0.007 | 0.003 | 0.469 | [0.419, 0.522] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.005 | 0.000 | 0.480 | [0.427, 0.528] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.000 | 0.003 | 0.514 | [0.469, 0.561] |
| ste-verbs.past-participle-not-adjectival | no | 0.090 | 0.084 | 0.514 | [0.473, 0.554] |
| ai-tells-structure.false-suspense-remainder | no | 0.000 | 0.000 | 0.492 | [0.439, 0.546] |
| ai-tells-register.hedged-symmetry | no | 0.007 | 0.002 | 0.505 | [0.462, 0.548] |
| ai-tells-content-shape.elegant-variation | no | 0.000 | 0.000 | 0.496 | [0.443, 0.540] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.018 | 0.006 | 0.496 | [0.447, 0.543] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.037 | 0.022 | 0.504 | [0.454, 0.556] |

## Per semantic rule, v3-kev-4b-ft-s18

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.021 | 0.187 | 0.810 | [0.772, 0.847] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.000 | 0.007 | 0.748 | [0.705, 0.791] |
| ai-tells-structure.summary-closer-remainder | no | 0.002 | 0.041 | 0.747 | [0.707, 0.787] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.005 | 0.013 | 0.731 | [0.685, 0.777] |
| ai-tells-content-shape.one-point-dilution | no | 0.011 | 0.051 | 0.729 | [0.684, 0.772] |
| ste-descriptive.missing-key-word-structure | no | 0.000 | 0.000 | 0.725 | [0.679, 0.771] |
| ste-verbs.gerund-outside-noun-use | no | 0.113 | 0.251 | 0.719 | [0.675, 0.762] |
| ste-sentences.sentence-not-short-or-clear | no | 0.000 | 0.062 | 0.718 | [0.680, 0.758] |
| ste-nouns.long-domain-term-without-short-form | no | 0.002 | 0.019 | 0.713 | [0.667, 0.760] |
| prose-discipline.marketing-register | no | 0.002 | 0.042 | 0.698 | [0.658, 0.741] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.002 | 0.022 | 0.695 | [0.655, 0.737] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.005 | 0.008 | 0.690 | [0.642, 0.734] |
| ste-descriptive.information-not-gradual | yes | 0.000 | 0.003 | 0.686 | [0.636, 0.733] |
| ai-tells-content-shape.padded-symmetry | no | 0.000 | 0.005 | 0.668 | [0.626, 0.714] |
| prose-discipline.overloaded-sentence | yes | 0.092 | 0.201 | 0.649 | [0.603, 0.692] |
| ai-tells-structure.false-range | yes | 0.000 | 0.000 | 0.356 | [0.315, 0.400] |
| ai-tells-register.over-formatting-reflex | no | 0.023 | 0.038 | 0.637 | [0.584, 0.689] |
| ai-tells-structure.audience-straddle-remainder | no | 0.000 | 0.000 | 0.635 | [0.589, 0.678] |
| ai-tells-structure.false-suspense-remainder | no | 0.000 | 0.002 | 0.635 | [0.588, 0.680] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.001 | 0.626 | [0.574, 0.674] |
| ste-descriptive.paragraph-without-related-information | no | 0.002 | 0.007 | 0.624 | [0.577, 0.673] |
| ste-punctuation.parentheses-misuse | no | 0.041 | 0.049 | 0.616 | [0.573, 0.662] |
| ai-tells-structure.vague-attribution-remainder | no | 0.007 | 0.003 | 0.608 | [0.562, 0.655] |
| ai-tells-content-shape.over-writing-remainder | no | 0.016 | 0.012 | 0.604 | [0.560, 0.648] |
| ai-tells-structure.heading-echo | no | 0.078 | 0.137 | 0.600 | [0.554, 0.650] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.000 | 0.000 | 0.600 | [0.557, 0.642] |
| ai-tells-register.faux-candor-remainder | no | 0.000 | 0.003 | 0.598 | [0.554, 0.642] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.009 | 0.007 | 0.590 | [0.549, 0.633] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.030 | 0.018 | 0.583 | [0.533, 0.634] |
| ai-tells-structure.meta-narration-remainder | yes | 0.014 | 0.016 | 0.580 | [0.532, 0.627] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.039 | 0.074 | 0.577 | [0.526, 0.625] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.005 | 0.002 | 0.574 | [0.525, 0.627] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.000 | 0.574 | [0.524, 0.621] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.016 | 0.023 | 0.566 | [0.517, 0.616] |
| prose-discipline.hedged-into-uselessness | no | 0.005 | 0.014 | 0.564 | [0.520, 0.608] |
| ai-tells-structure.hollow-acknowledgment | no | 0.005 | 0.015 | 0.560 | [0.519, 0.600] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.000 | 0.002 | 0.559 | [0.516, 0.609] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.005 | 0.009 | 0.442 | [0.393, 0.491] |
| ai-tells-content-shape.elegant-variation | no | 0.000 | 0.000 | 0.558 | [0.509, 0.604] |
| ai-tells-register.organic-consequence-remainder | no | 0.000 | 0.004 | 0.448 | [0.403, 0.492] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.006 | 0.551 | [0.501, 0.597] |
| ai-tells-structure.invented-concept-label | yes | 0.000 | 0.003 | 0.541 | [0.492, 0.592] |
| ai-tells-structure.anaphora-abuse | no | 0.007 | 0.004 | 0.531 | [0.484, 0.585] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.000 | 0.003 | 0.530 | [0.482, 0.581] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.000 | 0.472 | [0.422, 0.523] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.002 | 0.000 | 0.527 | [0.482, 0.576] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.004 | 0.527 | [0.477, 0.580] |
| ai-tells-register.hedged-symmetry | no | 0.007 | 0.000 | 0.527 | [0.484, 0.571] |
| ai-tells-structure.analogy-stack-authority | no | 0.000 | 0.002 | 0.523 | [0.477, 0.577] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.051 | 0.033 | 0.488 | [0.436, 0.542] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.000 | 0.003 | 0.490 | [0.441, 0.541] |
| ste-verbs.past-participle-not-adjectival | no | 0.060 | 0.058 | 0.509 | [0.467, 0.552] |
| ai-tells-register.false-agency-remainder | no | 0.007 | 0.008 | 0.492 | [0.449, 0.534] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.016 | 0.005 | 0.507 | [0.459, 0.552] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.002 | 0.001 | 0.501 | [0.452, 0.550] |

## Per semantic rule, v3-kev-4b-ft-s19

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.005 | 0.105 | 0.839 | [0.805, 0.869] |
| ai-tells-structure.summary-closer-remainder | no | 0.002 | 0.027 | 0.757 | [0.716, 0.799] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.000 | 0.001 | 0.748 | [0.707, 0.787] |
| ste-nouns.long-domain-term-without-short-form | no | 0.000 | 0.010 | 0.742 | [0.699, 0.787] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.002 | 0.029 | 0.737 | [0.699, 0.777] |
| ste-descriptive.missing-key-word-structure | no | 0.000 | 0.000 | 0.737 | [0.694, 0.778] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.007 | 0.008 | 0.722 | [0.679, 0.766] |
| ai-tells-structure.audience-straddle-remainder | no | 0.000 | 0.000 | 0.713 | [0.668, 0.754] |
| ste-sentences.sentence-not-short-or-clear | no | 0.002 | 0.046 | 0.701 | [0.662, 0.742] |
| ste-descriptive.information-not-gradual | yes | 0.000 | 0.002 | 0.694 | [0.649, 0.737] |
| prose-discipline.marketing-register | no | 0.000 | 0.023 | 0.693 | [0.653, 0.733] |
| ai-tells-content-shape.padded-symmetry | no | 0.000 | 0.001 | 0.681 | [0.635, 0.726] |
| ste-verbs.gerund-outside-noun-use | no | 0.097 | 0.185 | 0.666 | [0.622, 0.710] |
| prose-discipline.overloaded-sentence | yes | 0.085 | 0.194 | 0.664 | [0.617, 0.703] |
| ai-tells-register.faux-candor-remainder | no | 0.002 | 0.003 | 0.658 | [0.617, 0.701] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.000 | 0.000 | 0.657 | [0.608, 0.707] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.000 | 0.000 | 0.646 | [0.601, 0.692] |
| ai-tells-content-shape.one-point-dilution | no | 0.005 | 0.016 | 0.643 | [0.590, 0.695] |
| ai-tells-content-shape.over-writing-remainder | no | 0.014 | 0.006 | 0.638 | [0.594, 0.678] |
| ste-descriptive.paragraph-without-related-information | no | 0.000 | 0.005 | 0.626 | [0.573, 0.676] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.005 | 0.003 | 0.626 | [0.575, 0.674] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.000 | 0.004 | 0.390 | [0.342, 0.437] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.003 | 0.607 | [0.557, 0.655] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.601 | [0.548, 0.652] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.000 | 0.007 | 0.599 | [0.547, 0.649] |
| ai-tells-structure.vague-attribution-remainder | no | 0.005 | 0.001 | 0.599 | [0.549, 0.645] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.000 | 0.000 | 0.596 | [0.551, 0.640] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.000 | 0.593 | [0.548, 0.640] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.011 | 0.006 | 0.583 | [0.541, 0.622] |
| ai-tells-structure.heading-echo | no | 0.016 | 0.030 | 0.579 | [0.530, 0.629] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.007 | 0.025 | 0.573 | [0.528, 0.620] |
| ste-practices.ambiguous-preposition-with | no | 0.000 | 0.004 | 0.572 | [0.521, 0.619] |
| ai-tells-structure.hollow-acknowledgment | no | 0.000 | 0.009 | 0.569 | [0.525, 0.612] |
| prose-discipline.hedged-into-uselessness | no | 0.002 | 0.013 | 0.560 | [0.512, 0.602] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.002 | 0.007 | 0.558 | [0.507, 0.612] |
| ai-tells-register.hedged-symmetry | no | 0.005 | 0.000 | 0.557 | [0.516, 0.601] |
| ai-tells-structure.false-suspense-remainder | no | 0.000 | 0.000 | 0.547 | [0.494, 0.592] |
| ai-tells-structure.invented-concept-label | yes | 0.002 | 0.000 | 0.453 | [0.406, 0.498] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.000 | 0.000 | 0.460 | [0.404, 0.519] |
| ai-tells-register.false-agency-remainder | no | 0.007 | 0.005 | 0.537 | [0.490, 0.581] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.000 | 0.000 | 0.464 | [0.408, 0.523] |
| ai-tells-structure.anaphora-abuse | no | 0.011 | 0.004 | 0.467 | [0.416, 0.526] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.000 | 0.002 | 0.531 | [0.481, 0.582] |
| ai-tells-register.over-formatting-reflex | no | 0.009 | 0.018 | 0.529 | [0.479, 0.580] |
| ste-verbs.past-participle-not-adjectival | no | 0.090 | 0.081 | 0.528 | [0.487, 0.571] |
| ai-tells-structure.meta-narration-remainder | yes | 0.009 | 0.013 | 0.526 | [0.481, 0.570] |
| ai-tells-register.organic-consequence-remainder | no | 0.002 | 0.004 | 0.525 | [0.481, 0.568] |
| ai-tells-content-shape.elegant-variation | no | 0.000 | 0.000 | 0.522 | [0.472, 0.566] |
| ai-tells-structure.analogy-stack-authority | no | 0.000 | 0.001 | 0.517 | [0.471, 0.567] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.005 | 0.003 | 0.485 | [0.431, 0.533] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.055 | 0.036 | 0.487 | [0.431, 0.538] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.000 | 0.002 | 0.511 | [0.461, 0.562] |
| ai-tells-structure.false-range | yes | 0.000 | 0.000 | 0.499 | [0.453, 0.544] |
| ste-punctuation.parentheses-misuse | no | 0.023 | 0.010 | 0.499 | [0.450, 0.546] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.002 | 0.000 | 0.500 | [0.454, 0.543] |

## Per semantic rule, v3-kev-9b-ft-s17

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.122 | 0.607 | 0.898 | [0.868, 0.927] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.039 | 0.106 | 0.725 | [0.684, 0.767] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.295 | [0.253, 0.340] |
| ste-sentences.sentence-not-short-or-clear | no | 0.011 | 0.069 | 0.697 | [0.656, 0.736] |
| ste-verbs.gerund-outside-noun-use | no | 0.034 | 0.138 | 0.678 | [0.638, 0.716] |
| prose-discipline.marketing-register | no | 0.018 | 0.078 | 0.667 | [0.624, 0.715] |
| ste-nouns.long-domain-term-without-short-form | no | 0.007 | 0.010 | 0.646 | [0.596, 0.689] |
| ai-tells-content-shape.elegant-variation | no | 0.005 | 0.001 | 0.367 | [0.319, 0.417] |
| prose-discipline.overloaded-sentence | yes | 0.067 | 0.138 | 0.628 | [0.583, 0.673] |
| ai-tells-structure.heading-echo | no | 0.039 | 0.144 | 0.620 | [0.568, 0.672] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.004 | 0.611 | [0.562, 0.662] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.000 | 0.006 | 0.607 | [0.565, 0.651] |
| ste-practices.ambiguous-preposition-with | no | 0.002 | 0.000 | 0.597 | [0.550, 0.644] |
| ai-tells-structure.summary-closer-remainder | no | 0.018 | 0.045 | 0.593 | [0.540, 0.645] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.007 | 0.026 | 0.587 | [0.539, 0.635] |
| ai-tells-structure.false-range | yes | 0.000 | 0.000 | 0.584 | [0.543, 0.626] |
| ai-tells-register.organic-consequence-remainder | no | 0.002 | 0.013 | 0.584 | [0.540, 0.632] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.060 | 0.044 | 0.417 | [0.372, 0.466] |
| ai-tells-content-shape.padded-symmetry | no | 0.005 | 0.003 | 0.580 | [0.535, 0.628] |
| prose-discipline.hedged-into-uselessness | no | 0.007 | 0.025 | 0.579 | [0.530, 0.624] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.000 | 0.422 | [0.376, 0.466] |
| ai-tells-content-shape.over-writing-remainder | no | 0.002 | 0.004 | 0.422 | [0.372, 0.473] |
| ai-tells-structure.invented-concept-label | yes | 0.014 | 0.001 | 0.424 | [0.376, 0.472] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.002 | 0.022 | 0.574 | [0.526, 0.618] |
| ai-tells-register.hedged-symmetry | no | 0.009 | 0.008 | 0.573 | [0.532, 0.615] |
| ai-tells-structure.anaphora-abuse | no | 0.005 | 0.011 | 0.571 | [0.520, 0.621] |
| ai-tells-structure.analogy-stack-authority | no | 0.002 | 0.000 | 0.432 | [0.383, 0.479] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.028 | 0.038 | 0.562 | [0.516, 0.608] |
| ai-tells-register.false-agency-remainder | no | 0.023 | 0.013 | 0.561 | [0.513, 0.608] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.037 | 0.012 | 0.442 | [0.389, 0.491] |
| ai-tells-structure.vague-attribution-remainder | no | 0.025 | 0.019 | 0.557 | [0.511, 0.601] |
| ste-descriptive.paragraph-without-related-information | no | 0.009 | 0.024 | 0.554 | [0.509, 0.602] |
| ste-descriptive.missing-key-word-structure | no | 0.007 | 0.007 | 0.552 | [0.509, 0.595] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.037 | 0.015 | 0.451 | [0.402, 0.502] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.002 | 0.003 | 0.457 | [0.407, 0.509] |
| ai-tells-structure.hollow-acknowledgment | no | 0.023 | 0.036 | 0.543 | [0.504, 0.583] |
| ai-tells-structure.meta-narration-remainder | yes | 0.034 | 0.053 | 0.542 | [0.490, 0.590] |
| ai-tells-content-shape.one-point-dilution | no | 0.023 | 0.016 | 0.541 | [0.490, 0.593] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.000 | 0.006 | 0.537 | [0.489, 0.584] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.000 | 0.005 | 0.465 | [0.418, 0.514] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.002 | 0.003 | 0.535 | [0.483, 0.587] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.009 | 0.014 | 0.533 | [0.479, 0.587] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.002 | 0.003 | 0.532 | [0.497, 0.569] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.005 | 0.004 | 0.474 | [0.426, 0.521] |
| ai-tells-register.faux-candor-remainder | no | 0.000 | 0.000 | 0.474 | [0.426, 0.521] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.057 | 0.038 | 0.522 | [0.478, 0.568] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.044 | 0.032 | 0.479 | [0.425, 0.530] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.009 | 0.003 | 0.519 | [0.469, 0.565] |
| ste-punctuation.parentheses-misuse | no | 0.057 | 0.055 | 0.482 | [0.434, 0.529] |
| ste-verbs.past-participle-not-adjectival | no | 0.071 | 0.060 | 0.516 | [0.468, 0.562] |
| ai-tells-register.over-formatting-reflex | no | 0.030 | 0.054 | 0.513 | [0.462, 0.563] |
| ai-tells-structure.audience-straddle-remainder | no | 0.002 | 0.002 | 0.513 | [0.466, 0.557] |
| ai-tells-structure.false-suspense-remainder | no | 0.002 | 0.008 | 0.488 | [0.439, 0.541] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.002 | 0.001 | 0.493 | [0.447, 0.545] |
| ste-descriptive.information-not-gradual | yes | 0.009 | 0.006 | 0.495 | [0.450, 0.541] |

## Per semantic rule, v3-kev-9b-ft-s18

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.078 | 0.445 | 0.869 | [0.836, 0.899] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.002 | 0.001 | 0.275 | [0.236, 0.320] |
| ste-verbs.gerund-outside-noun-use | no | 0.097 | 0.244 | 0.724 | [0.685, 0.766] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.000 | 0.000 | 0.290 | [0.247, 0.333] |
| ste-nouns.long-domain-term-without-short-form | no | 0.039 | 0.072 | 0.691 | [0.644, 0.733] |
| prose-discipline.marketing-register | no | 0.023 | 0.085 | 0.670 | [0.625, 0.716] |
| ste-sentences.sentence-not-short-or-clear | no | 0.032 | 0.101 | 0.662 | [0.619, 0.704] |
| ai-tells-content-shape.elegant-variation | no | 0.002 | 0.001 | 0.340 | [0.293, 0.386] |
| ai-tells-content-shape.padded-symmetry | no | 0.011 | 0.002 | 0.344 | [0.299, 0.392] |
| ai-tells-register.false-agency-remainder | no | 0.032 | 0.033 | 0.645 | [0.600, 0.690] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.039 | 0.055 | 0.643 | [0.598, 0.692] |
| ai-tells-content-shape.over-writing-remainder | no | 0.030 | 0.005 | 0.358 | [0.314, 0.405] |
| ai-tells-structure.false-range | yes | 0.000 | 0.007 | 0.633 | [0.591, 0.678] |
| ai-tells-structure.false-suspense-remainder | no | 0.000 | 0.003 | 0.367 | [0.320, 0.415] |
| ai-tells-structure.invented-concept-label | yes | 0.023 | 0.002 | 0.379 | [0.331, 0.426] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.005 | 0.004 | 0.387 | [0.350, 0.426] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.025 | 0.010 | 0.389 | [0.343, 0.438] |
| ai-tells-register.organic-consequence-remainder | no | 0.005 | 0.021 | 0.607 | [0.563, 0.652] |
| ai-tells-register.faux-candor-remainder | no | 0.000 | 0.002 | 0.396 | [0.349, 0.444] |
| prose-discipline.overloaded-sentence | yes | 0.055 | 0.088 | 0.602 | [0.557, 0.647] |
| ai-tells-structure.heading-echo | no | 0.057 | 0.108 | 0.602 | [0.551, 0.653] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.002 | 0.006 | 0.601 | [0.552, 0.649] |
| prose-discipline.competing-actor-terms | no | 0.000 | 0.003 | 0.411 | [0.365, 0.452] |
| ste-punctuation.parentheses-misuse | no | 0.087 | 0.044 | 0.411 | [0.364, 0.457] |
| ai-tells-content-shape.one-point-dilution | no | 0.037 | 0.031 | 0.586 | [0.535, 0.635] |
| ai-tells-structure.analogy-stack-authority | no | 0.002 | 0.000 | 0.418 | [0.373, 0.462] |
| ai-tells-structure.anaphora-abuse | no | 0.005 | 0.014 | 0.578 | [0.533, 0.627] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.002 | 0.020 | 0.577 | [0.535, 0.622] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.094 | 0.062 | 0.423 | [0.381, 0.467] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.016 | 0.037 | 0.574 | [0.531, 0.620] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.000 | 0.005 | 0.574 | [0.527, 0.624] |
| ste-descriptive.missing-key-word-structure | no | 0.002 | 0.001 | 0.430 | [0.387, 0.480] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.002 | 0.008 | 0.559 | [0.511, 0.603] |
| ste-descriptive.information-not-gradual | yes | 0.007 | 0.011 | 0.442 | [0.398, 0.486] |
| ai-tells-register.hedged-symmetry | no | 0.011 | 0.014 | 0.541 | [0.502, 0.581] |
| ai-tells-structure.vague-attribution-remainder | no | 0.053 | 0.062 | 0.540 | [0.493, 0.588] |
| ste-descriptive.paragraph-without-related-information | no | 0.090 | 0.089 | 0.463 | [0.426, 0.506] |
| ai-tells-structure.meta-narration-remainder | yes | 0.030 | 0.051 | 0.535 | [0.484, 0.582] |
| ste-verbs.past-participle-not-adjectival | no | 0.067 | 0.101 | 0.533 | [0.486, 0.577] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.018 | 0.029 | 0.533 | [0.480, 0.584] |
| ste-practices.ambiguous-preposition-with | no | 0.002 | 0.003 | 0.529 | [0.483, 0.575] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.005 | 0.010 | 0.474 | [0.426, 0.521] |
| ai-tells-structure.hollow-acknowledgment | no | 0.025 | 0.016 | 0.474 | [0.433, 0.514] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.007 | 0.018 | 0.524 | [0.477, 0.569] |
| ai-tells-register.over-formatting-reflex | no | 0.055 | 0.097 | 0.477 | [0.432, 0.525] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.051 | 0.049 | 0.481 | [0.435, 0.533] |
| ai-tells-structure.audience-straddle-remainder | no | 0.002 | 0.001 | 0.485 | [0.442, 0.527] |
| prose-discipline.hedged-into-uselessness | no | 0.014 | 0.027 | 0.515 | [0.473, 0.553] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.044 | 0.036 | 0.485 | [0.430, 0.539] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.018 | 0.021 | 0.509 | [0.459, 0.556] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.009 | 0.003 | 0.493 | [0.445, 0.541] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.000 | 0.005 | 0.506 | [0.457, 0.554] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.014 | 0.010 | 0.505 | [0.456, 0.554] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.044 | 0.027 | 0.504 | [0.461, 0.547] |
| ai-tells-structure.summary-closer-remainder | no | 0.018 | 0.034 | 0.503 | [0.455, 0.552] |

## Per semantic rule, v3-kev-9b-ft-s19

Score: the document's mean p(yes) for the rule over its regions.

| rule | held out | human yes rate | generated yes rate | AUC | 95% CI |
|---|---|---|---|---|---|
| orwell.concrete-floor | no | 0.064 | 0.366 | 0.864 | [0.833, 0.895] |
| ste-verbs.gerund-outside-noun-use | no | 0.034 | 0.122 | 0.698 | [0.658, 0.736] |
| ste-sentences.sentence-not-short-or-clear | no | 0.007 | 0.039 | 0.682 | [0.639, 0.721] |
| ai-tells-content-shape.over-writing-remainder | no | 0.009 | 0.001 | 0.318 | [0.276, 0.363] |
| ai-tells-structure.think-of-it-as-remainder | no | 0.002 | 0.001 | 0.322 | [0.277, 0.367] |
| ai-tells-structure.false-suspense-remainder | no | 0.000 | 0.003 | 0.325 | [0.282, 0.367] |
| ste-descriptive.paragraph-has-multiple-topics | no | 0.041 | 0.088 | 0.671 | [0.631, 0.712] |
| ste-nouns.long-domain-term-without-short-form | no | 0.025 | 0.023 | 0.667 | [0.618, 0.711] |
| ai-tells-content-shape.unasked-for-rationale | yes | 0.032 | 0.005 | 0.340 | [0.301, 0.381] |
| ai-tells-content-shape.padded-symmetry | no | 0.007 | 0.002 | 0.346 | [0.300, 0.392] |
| prose-discipline.marketing-register | no | 0.018 | 0.071 | 0.647 | [0.604, 0.688] |
| ai-tells-structure.tricolon-abuse-remainder | no | 0.002 | 0.000 | 0.359 | [0.316, 0.405] |
| ai-tells-register.faux-candor-remainder | no | 0.000 | 0.000 | 0.380 | [0.336, 0.425] |
| prose-discipline.overloaded-sentence | yes | 0.032 | 0.104 | 0.616 | [0.573, 0.658] |
| ai-tells-content-shape.one-point-dilution | no | 0.018 | 0.023 | 0.615 | [0.564, 0.665] |
| ai-tells-structure.false-range | yes | 0.005 | 0.004 | 0.606 | [0.558, 0.651] |
| ai-tells-structure.cataphoric-lead-in-remainder | no | 0.021 | 0.004 | 0.396 | [0.346, 0.446] |
| ai-tells-register.intensifier-tics-remainder | yes | 0.002 | 0.001 | 0.397 | [0.352, 0.443] |
| ai-tells-content-shape.textbook-connector-runs | yes | 0.000 | 0.009 | 0.602 | [0.553, 0.649] |
| ai-tells-structure.heading-echo | no | 0.039 | 0.113 | 0.600 | [0.549, 0.649] |
| ai-tells-content-shape.elegant-variation | no | 0.007 | 0.001 | 0.402 | [0.357, 0.451] |
| ai-tells-structure.analogy-stack-authority | no | 0.005 | 0.000 | 0.404 | [0.358, 0.450] |
| ai-tells-structure.negative-inventory-remainder | yes | 0.051 | 0.029 | 0.408 | [0.367, 0.453] |
| ai-tells-structure.invented-concept-label | yes | 0.014 | 0.003 | 0.412 | [0.365, 0.454] |
| ai-tells-register.false-agency-remainder | no | 0.011 | 0.016 | 0.588 | [0.540, 0.637] |
| ai-tells-structure.meta-narration-remainder | yes | 0.016 | 0.023 | 0.414 | [0.362, 0.463] |
| ai-tells-formatting.table-wrapping-one-sentence | no | 0.039 | 0.024 | 0.415 | [0.365, 0.466] |
| ai-tells-structure.staccato-negative-parallel-remainder | no | 0.000 | 0.002 | 0.581 | [0.528, 0.629] |
| ste-punctuation.parentheses-misuse | no | 0.037 | 0.022 | 0.421 | [0.375, 0.466] |
| ai-tells-register.figurative-verb-verdict-remainder | no | 0.005 | 0.002 | 0.422 | [0.380, 0.468] |
| ste-descriptive.missing-key-word-structure | no | 0.014 | 0.003 | 0.430 | [0.386, 0.480] |
| ste-practices.ambiguous-preposition-with | no | 0.002 | 0.000 | 0.568 | [0.523, 0.615] |
| ai-tells-structure.vague-attribution-remainder | no | 0.025 | 0.033 | 0.567 | [0.522, 0.611] |
| ai-tells-structure.anaphora-abuse | no | 0.005 | 0.011 | 0.564 | [0.514, 0.612] |
| prose-discipline.competing-actor-terms | no | 0.002 | 0.001 | 0.443 | [0.397, 0.487] |
| ste-safety.risk-level-word-missing-or-wrong | no | 0.007 | 0.004 | 0.443 | [0.403, 0.484] |
| ste-descriptive.information-not-gradual | yes | 0.002 | 0.004 | 0.445 | [0.400, 0.488] |
| ai-tells-register.hedged-symmetry | no | 0.009 | 0.010 | 0.551 | [0.512, 0.593] |
| ai-tells-register.organic-consequence-remainder | no | 0.014 | 0.010 | 0.450 | [0.408, 0.494] |
| ai-tells-structure.summary-closer-remainder | no | 0.023 | 0.035 | 0.548 | [0.498, 0.596] |
| ai-tells-structure.audience-straddle-remainder | no | 0.005 | 0.005 | 0.547 | [0.501, 0.592] |
| ai-tells-register.over-formatting-reflex | no | 0.055 | 0.075 | 0.459 | [0.414, 0.507] |
| ai-tells-structure.hollow-acknowledgment | no | 0.009 | 0.011 | 0.462 | [0.421, 0.503] |
| ai-tells-structure.absolute-assertion-remainder | no | 0.002 | 0.008 | 0.466 | [0.421, 0.511] |
| ai-tells-register.urgency-inflation-remainder | yes | 0.002 | 0.004 | 0.530 | [0.484, 0.573] |
| ste-words.domain-noun-too-long-or-unclear | no | 0.007 | 0.003 | 0.528 | [0.475, 0.576] |
| ai-tells-structure.contrastive-inversion-remainder | no | 0.002 | 0.003 | 0.526 | [0.482, 0.569] |
| prose-discipline.hedged-into-uselessness | no | 0.005 | 0.017 | 0.518 | [0.471, 0.560] |
| prose-discipline.bare-quantifier-with-figure-available | no | 0.041 | 0.031 | 0.487 | [0.432, 0.537] |
| ste-verbs.past-participle-not-adjectival | no | 0.046 | 0.054 | 0.509 | [0.462, 0.551] |
| ste-descriptive.paragraph-without-related-information | no | 0.011 | 0.004 | 0.509 | [0.464, 0.555] |
| ai-tells-content-shape.epigram-closer-remainder | no | 0.000 | 0.002 | 0.492 | [0.447, 0.537] |
| ste-sentences.missing-connector-between-related-sentences | no | 0.014 | 0.027 | 0.505 | [0.463, 0.547] |
| ai-tells-structure.listicle-in-a-trench-coat | no | 0.005 | 0.013 | 0.505 | [0.454, 0.558] |
| ai-tells-register.anthropomorphised-justification-remainder | no | 0.007 | 0.010 | 0.497 | [0.452, 0.540] |
