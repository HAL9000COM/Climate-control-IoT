import math


def mean_radiant_temperature(Ta, GT, va):
    Dg = 0.16
    Epsilon = 0.95
    Tmrt = (
        math.pow(
            (
                math.pow(GT + 273.15, 4)
                + (1.1e8 * math.pow(va, 0.6) * (GT - Ta)) / Epsilon * math.pow(Dg, 0.4)
            ),
            0.25,
        )
        - 273.15
    )
    return Tmrt


def universal_thermal_climate_index(Ta, GT, RH, va):
    """Calculate Universal Thermal Climate Index (UTCI) using a polynomial approximation.

    UTCI is an international standard for outdoor temperature sensation
    (aka. "feels-like" temperature) that attempts to fill the
    following requirements:

    1) Thermo-physiological significance in the whole range of heat
       exchange conditions of existing thermal environments
    2) Valid in all climates, seasons, and scales
    3) Useful for key applications in human biometeorology.

    This function here is a Python version of the original UTCI_approx
    application written in Fortran. Version a 0.002, October 2009
    The original Fortran code can be found at www.utci.org.

    Note:
        [1] Peter Bröde, Dusan Fiala, Krzysztof Blazejczyk, Yoram Epstein,
        Ingvar Holmér, Gerd Jendritzky, Bernhard Kampmann, Mark Richards,
        Hannu Rintamäki, Avraham Shitzer, George Havenith. 2009.
        Calculating UTCI Equivalent Temperature. In: JW Castellani & TL
        Endrusick, eds. Proceedings of the 13th International Conference
        on Environmental Ergonomics, USARIEM, Natick, MA.

    Args:
        Ta: Air temperature [C]
        Tmrt: Mean radiant temperature [C]
        vel: Wind speed 10 m above ground level [m/s].
            Note that this meteorological speed at 10 m is simply 1.5 times the
            speed felt at ground in the original Fiala model used to build UTCI.
        RH: Relative humidity [%]

    Returns:
        UTCI_approx -- The Universal Thermal Climate Index (UTCI) for the input
        conditions as approximated by a 4-D polynomial.
    """
    vel = va * 1.5
    va = 0 if va < 0 else va
    Tmrt = mean_radiant_temperature(Ta, GT, va)

    # set upper and lower limits of air velocity according to Fiala model scenarios
    vel = 0.5 if vel < 0.5 else vel
    vel = 17 if vel > 17 else vel

    # metrics derived from the inputs used in the polynomial equation
    eh_pa = saturated_vapor_pressure_hpa(Ta) * (RH / 100.0)  # partial vapor pressure
    pa_pr = eh_pa / 10.0  # convert vapour pressure to kPa
    d_Tmrt = Tmrt - Ta  # difference between radiant and air temperature

    utci_approx = (
        Ta
        + 0.607562052
        + -0.0227712343 * Ta
        + 8.06470249e-4 * Ta * Ta
        + -1.54271372e-4 * Ta * Ta * Ta
        + -3.24651735e-6 * Ta * Ta * Ta * Ta
        + 7.32602852e-8 * Ta * Ta * Ta * Ta * Ta
        + 1.35959073e-9 * Ta * Ta * Ta * Ta * Ta * Ta
        + -2.25836520 * vel
        + 0.0880326035 * Ta * vel
        + 0.00216844454 * Ta * Ta * vel
        + -1.53347087e-5 * Ta * Ta * Ta * vel
        + -5.72983704e-7 * Ta * Ta * Ta * Ta * vel
        + -2.55090145e-9 * Ta * Ta * Ta * Ta * Ta * vel
        + -0.751269505 * vel * vel
        + -0.00408350271 * Ta * vel * vel
        + -5.21670675e-5 * Ta * Ta * vel * vel
        + 1.94544667e-6 * Ta * Ta * Ta * vel * vel
        + 1.14099531e-8 * Ta * Ta * Ta * Ta * vel * vel
        + 0.158137256 * vel * vel * vel
        + -6.57263143e-5 * Ta * vel * vel * vel
        + 2.22697524e-7 * Ta * Ta * vel * vel * vel
        + -4.16117031e-8 * Ta * Ta * Ta * vel * vel * vel
        + -0.0127762753 * vel * vel * vel * vel
        + 9.66891875e-6 * Ta * vel * vel * vel * vel
        + 2.52785852e-9 * Ta * Ta * vel * vel * vel * vel
        + 4.56306672e-4 * vel * vel * vel * vel * vel
        + -1.74202546e-7 * Ta * vel * vel * vel * vel * vel
        + -5.91491269e-6 * vel * vel * vel * vel * vel * vel
        + 0.398374029 * d_Tmrt
        + 1.83945314e-4 * Ta * d_Tmrt
        + -1.73754510e-4 * Ta * Ta * d_Tmrt
        + -7.60781159e-7 * Ta * Ta * Ta * d_Tmrt
        + 3.77830287e-8 * Ta * Ta * Ta * Ta * d_Tmrt
        + 5.43079673e-10 * Ta * Ta * Ta * Ta * Ta * d_Tmrt
        + -0.0200518269 * vel * d_Tmrt
        + 8.92859837e-4 * Ta * vel * d_Tmrt
        + 3.45433048e-6 * Ta * Ta * vel * d_Tmrt
        + -3.77925774e-7 * Ta * Ta * Ta * vel * d_Tmrt
        + -1.69699377e-9 * Ta * Ta * Ta * Ta * vel * d_Tmrt
        + 1.69992415e-4 * vel * vel * d_Tmrt
        + -4.99204314e-5 * Ta * vel * vel * d_Tmrt
        + 2.47417178e-7 * Ta * Ta * vel * vel * d_Tmrt
        + 1.07596466e-8 * Ta * Ta * Ta * vel * vel * d_Tmrt
        + 8.49242932e-5 * vel * vel * vel * d_Tmrt
        + 1.35191328e-6 * Ta * vel * vel * vel * d_Tmrt
        + -6.21531254e-9 * Ta * Ta * vel * vel * vel * d_Tmrt
        + -4.99410301e-6 * vel * vel * vel * vel * d_Tmrt
        + -1.89489258e-8 * Ta * vel * vel * vel * vel * d_Tmrt
        + 8.15300114e-8 * vel * vel * vel * vel * vel * d_Tmrt
        + 7.55043090e-4 * d_Tmrt * d_Tmrt
        + -5.65095215e-5 * Ta * d_Tmrt * d_Tmrt
        + -4.52166564e-7 * Ta * Ta * d_Tmrt * d_Tmrt
        + 2.46688878e-8 * Ta * Ta * Ta * d_Tmrt * d_Tmrt
        + 2.42674348e-10 * Ta * Ta * Ta * Ta * d_Tmrt * d_Tmrt
        + 1.54547250e-4 * vel * d_Tmrt * d_Tmrt
        + 5.24110970e-6 * Ta * vel * d_Tmrt * d_Tmrt
        + -8.75874982e-8 * Ta * Ta * vel * d_Tmrt * d_Tmrt
        + -1.50743064e-9 * Ta * Ta * Ta * vel * d_Tmrt * d_Tmrt
        + -1.56236307e-5 * vel * vel * d_Tmrt * d_Tmrt
        + -1.33895614e-7 * Ta * vel * vel * d_Tmrt * d_Tmrt
        + 2.49709824e-9 * Ta * Ta * vel * vel * d_Tmrt * d_Tmrt
        + 6.51711721e-7 * vel * vel * vel * d_Tmrt * d_Tmrt
        + 1.94960053e-9 * Ta * vel * vel * vel * d_Tmrt * d_Tmrt
        + -1.00361113e-8 * vel * vel * vel * vel * d_Tmrt * d_Tmrt
        + -1.21206673e-5 * d_Tmrt * d_Tmrt * d_Tmrt
        + -2.18203660e-7 * Ta * d_Tmrt * d_Tmrt * d_Tmrt
        + 7.51269482e-9 * Ta * Ta * d_Tmrt * d_Tmrt * d_Tmrt
        + 9.79063848e-11 * Ta * Ta * Ta * d_Tmrt * d_Tmrt * d_Tmrt
        + 1.25006734e-6 * vel * d_Tmrt * d_Tmrt * d_Tmrt
        + -1.81584736e-9 * Ta * vel * d_Tmrt * d_Tmrt * d_Tmrt
        + -3.52197671e-10 * Ta * Ta * vel * d_Tmrt * d_Tmrt * d_Tmrt
        + -3.36514630e-8 * vel * vel * d_Tmrt * d_Tmrt * d_Tmrt
        + 1.35908359e-10 * Ta * vel * vel * d_Tmrt * d_Tmrt * d_Tmrt
        + 4.17032620e-10 * vel * vel * vel * d_Tmrt * d_Tmrt * d_Tmrt
        + -1.30369025e-9 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + 4.13908461e-10 * Ta * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + 9.22652254e-12 * Ta * Ta * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + -5.08220384e-9 * vel * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + -2.24730961e-11 * Ta * vel * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + 1.17139133e-10 * vel * vel * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + 6.62154879e-10 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + 4.03863260e-13 * Ta * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + 1.95087203e-12 * vel * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + -4.73602469e-12 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt
        + 5.12733497 * pa_pr
        + -0.312788561 * Ta * pa_pr
        + -0.0196701861 * Ta * Ta * pa_pr
        + 9.99690870e-4 * Ta * Ta * Ta * pa_pr
        + 9.51738512e-6 * Ta * Ta * Ta * Ta * pa_pr
        + -4.66426341e-7 * Ta * Ta * Ta * Ta * Ta * pa_pr
        + 0.548050612 * vel * pa_pr
        + -0.00330552823 * Ta * vel * pa_pr
        + -0.00164119440 * Ta * Ta * vel * pa_pr
        + -5.16670694e-6 * Ta * Ta * Ta * vel * pa_pr
        + 9.52692432e-7 * Ta * Ta * Ta * Ta * vel * pa_pr
        + -0.0429223622 * vel * vel * pa_pr
        + 0.00500845667 * Ta * vel * vel * pa_pr
        + 1.00601257e-6 * Ta * Ta * vel * vel * pa_pr
        + -1.81748644e-6 * Ta * Ta * Ta * vel * vel * pa_pr
        + -1.25813502e-3 * vel * vel * vel * pa_pr
        + -1.79330391e-4 * Ta * vel * vel * vel * pa_pr
        + 2.34994441e-6 * Ta * Ta * vel * vel * vel * pa_pr
        + 1.29735808e-4 * vel * vel * vel * vel * pa_pr
        + 1.29064870e-6 * Ta * vel * vel * vel * vel * pa_pr
        + -2.28558686e-6 * vel * vel * vel * vel * vel * pa_pr
        + -0.0369476348 * d_Tmrt * pa_pr
        + 0.00162325322 * Ta * d_Tmrt * pa_pr
        + -3.14279680e-5 * Ta * Ta * d_Tmrt * pa_pr
        + 2.59835559e-6 * Ta * Ta * Ta * d_Tmrt * pa_pr
        + -4.77136523e-8 * Ta * Ta * Ta * Ta * d_Tmrt * pa_pr
        + 8.64203390e-3 * vel * d_Tmrt * pa_pr
        + -6.87405181e-4 * Ta * vel * d_Tmrt * pa_pr
        + -9.13863872e-6 * Ta * Ta * vel * d_Tmrt * pa_pr
        + 5.15916806e-7 * Ta * Ta * Ta * vel * d_Tmrt * pa_pr
        + -3.59217476e-5 * vel * vel * d_Tmrt * pa_pr
        + 3.28696511e-5 * Ta * vel * vel * d_Tmrt * pa_pr
        + -7.10542454e-7 * Ta * Ta * vel * vel * d_Tmrt * pa_pr
        + -1.24382300e-5 * vel * vel * vel * d_Tmrt * pa_pr
        + -7.38584400e-9 * Ta * vel * vel * vel * d_Tmrt * pa_pr
        + 2.20609296e-7 * vel * vel * vel * vel * d_Tmrt * pa_pr
        + -7.32469180e-4 * d_Tmrt * d_Tmrt * pa_pr
        + -1.87381964e-5 * Ta * d_Tmrt * d_Tmrt * pa_pr
        + 4.80925239e-6 * Ta * Ta * d_Tmrt * d_Tmrt * pa_pr
        + -8.75492040e-8 * Ta * Ta * Ta * d_Tmrt * d_Tmrt * pa_pr
        + 2.77862930e-5 * vel * d_Tmrt * d_Tmrt * pa_pr
        + -5.06004592e-6 * Ta * vel * d_Tmrt * d_Tmrt * pa_pr
        + 1.14325367e-7 * Ta * Ta * vel * d_Tmrt * d_Tmrt * pa_pr
        + 2.53016723e-6 * vel * vel * d_Tmrt * d_Tmrt * pa_pr
        + -1.72857035e-8 * Ta * vel * vel * d_Tmrt * d_Tmrt * pa_pr
        + -3.95079398e-8 * vel * vel * vel * d_Tmrt * d_Tmrt * pa_pr
        + -3.59413173e-7 * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + 7.04388046e-7 * Ta * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + -1.89309167e-8 * Ta * Ta * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + -4.79768731e-7 * vel * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + 7.96079978e-9 * Ta * vel * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + 1.62897058e-9 * vel * vel * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + 3.94367674e-8 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + -1.18566247e-9 * Ta * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + 3.34678041e-10 * vel * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + -1.15606447e-10 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr
        + -2.80626406 * pa_pr * pa_pr
        + 0.548712484 * Ta * pa_pr * pa_pr
        + -0.00399428410 * Ta * Ta * pa_pr * pa_pr
        + -9.54009191e-4 * Ta * Ta * Ta * pa_pr * pa_pr
        + 1.93090978e-5 * Ta * Ta * Ta * Ta * pa_pr * pa_pr
        + -0.308806365 * vel * pa_pr * pa_pr
        + 0.0116952364 * Ta * vel * pa_pr * pa_pr
        + 4.95271903e-4 * Ta * Ta * vel * pa_pr * pa_pr
        + -1.90710882e-5 * Ta * Ta * Ta * vel * pa_pr * pa_pr
        + 0.00210787756 * vel * vel * pa_pr * pa_pr
        + -6.98445738e-4 * Ta * vel * vel * pa_pr * pa_pr
        + 2.30109073e-5 * Ta * Ta * vel * vel * pa_pr * pa_pr
        + 4.17856590e-4 * vel * vel * vel * pa_pr * pa_pr
        + -1.27043871e-5 * Ta * vel * vel * vel * pa_pr * pa_pr
        + -3.04620472e-6 * vel * vel * vel * vel * pa_pr * pa_pr
        + 0.0514507424 * d_Tmrt * pa_pr * pa_pr
        + -0.00432510997 * Ta * d_Tmrt * pa_pr * pa_pr
        + 8.99281156e-5 * Ta * Ta * d_Tmrt * pa_pr * pa_pr
        + -7.14663943e-7 * Ta * Ta * Ta * d_Tmrt * pa_pr * pa_pr
        + -2.66016305e-4 * vel * d_Tmrt * pa_pr * pa_pr
        + 2.63789586e-4 * Ta * vel * d_Tmrt * pa_pr * pa_pr
        + -7.01199003e-6 * Ta * Ta * vel * d_Tmrt * pa_pr * pa_pr
        + -1.06823306e-4 * vel * vel * d_Tmrt * pa_pr * pa_pr
        + 3.61341136e-6 * Ta * vel * vel * d_Tmrt * pa_pr * pa_pr
        + 2.29748967e-7 * vel * vel * vel * d_Tmrt * pa_pr * pa_pr
        + 3.04788893e-4 * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + -6.42070836e-5 * Ta * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + 1.16257971e-6 * Ta * Ta * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + 7.68023384e-6 * vel * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + -5.47446896e-7 * Ta * vel * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + -3.59937910e-8 * vel * vel * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + -4.36497725e-6 * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + 1.68737969e-7 * Ta * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + 2.67489271e-8 * vel * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + 3.23926897e-9 * d_Tmrt * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr
        + -0.0353874123 * pa_pr * pa_pr * pa_pr
        + -0.221201190 * Ta * pa_pr * pa_pr * pa_pr
        + 0.0155126038 * Ta * Ta * pa_pr * pa_pr * pa_pr
        + -2.63917279e-4 * Ta * Ta * Ta * pa_pr * pa_pr * pa_pr
        + 0.0453433455 * vel * pa_pr * pa_pr * pa_pr
        + -0.00432943862 * Ta * vel * pa_pr * pa_pr * pa_pr
        + 1.45389826e-4 * Ta * Ta * vel * pa_pr * pa_pr * pa_pr
        + 2.17508610e-4 * vel * vel * pa_pr * pa_pr * pa_pr
        + -6.66724702e-5 * Ta * vel * vel * pa_pr * pa_pr * pa_pr
        + 3.33217140e-5 * vel * vel * vel * pa_pr * pa_pr * pa_pr
        + -0.00226921615 * d_Tmrt * pa_pr * pa_pr * pa_pr
        + 3.80261982e-4 * Ta * d_Tmrt * pa_pr * pa_pr * pa_pr
        + -5.45314314e-9 * Ta * Ta * d_Tmrt * pa_pr * pa_pr * pa_pr
        + -7.96355448e-4 * vel * d_Tmrt * pa_pr * pa_pr * pa_pr
        + 2.53458034e-5 * Ta * vel * d_Tmrt * pa_pr * pa_pr * pa_pr
        + -6.31223658e-6 * vel * vel * d_Tmrt * pa_pr * pa_pr * pa_pr
        + 3.02122035e-4 * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr
        + -4.77403547e-6 * Ta * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr
        + 1.73825715e-6 * vel * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr
        + -4.09087898e-7 * d_Tmrt * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr
        + 0.614155345 * pa_pr * pa_pr * pa_pr * pa_pr
        + -0.0616755931 * Ta * pa_pr * pa_pr * pa_pr * pa_pr
        + 0.00133374846 * Ta * Ta * pa_pr * pa_pr * pa_pr * pa_pr
        + 0.00355375387 * vel * pa_pr * pa_pr * pa_pr * pa_pr
        + -5.13027851e-4 * Ta * vel * pa_pr * pa_pr * pa_pr * pa_pr
        + 1.02449757e-4 * vel * vel * pa_pr * pa_pr * pa_pr * pa_pr
        + -0.00148526421 * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr
        + -4.11469183e-5 * Ta * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr
        + -6.80434415e-6 * vel * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr
        + -9.77675906e-6 * d_Tmrt * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr
        + 0.0882773108 * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr
        + -0.00301859306 * Ta * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr
        + 0.00104452989 * vel * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr
        + 2.47090539e-4 * d_Tmrt * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr
        + 0.00148348065 * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr * pa_pr
    )

    return utci_approx


def saturated_vapor_pressure_hpa(db_temp):
    """Calculate saturated vapor pressure (hPa) at temperature (C).

    This equation of saturation vapor pressure is specific to the UTCI model.
    """
    g = (
        -2836.5744,
        -6028.076559,
        19.54263612,
        -0.02737830188,
        0.000016261698,
        7.0229056e-10,
        -1.8680009e-13,
    )
    tk = db_temp + 273.15  # air temp in K
    es = 2.7150305 * math.log(tk)
    for i, x in enumerate(g):
        es = es + (x * (tk ** (i - 2)))
    es = math.exp(es) * 0.01
    return es
