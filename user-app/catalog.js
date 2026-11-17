const catalog = [
  {
    "id": "sirius",
    "name": "Sirius",
    "category": "star",
    "ra_deg": 101.2872,
    "dec_deg": -16.7161,
    "magnitude": -1.46,
    "distance": "About 8.6 light-years",
    "description": "The brightest star in the night sky, in Canis Major."
  },
  {
    "id": "canopus",
    "name": "Canopus",
    "category": "star",
    "ra_deg": 95.9879,
    "dec_deg": -52.6957,
    "magnitude": -0.74,
    "distance": "About 310 light-years",
    "description": "A luminous southern star in Carina."
  },
  {
    "id": "arcturus",
    "name": "Arcturus",
    "category": "star",
    "ra_deg": 213.9153,
    "dec_deg": 19.1824,
    "magnitude": -0.05,
    "distance": "About 37 light-years",
    "description": "An orange giant in Bootes. Its color reflects a cooler surface than the Sun."
  },
  {
    "id": "vega",
    "name": "Vega",
    "category": "star",
    "ra_deg": 279.2347,
    "dec_deg": 38.7837,
    "magnitude": 0.03,
    "distance": "About 25 light-years",
    "description": "A bright star in Lyra and one corner of the Summer Triangle."
  },
  {
    "id": "capella",
    "name": "Capella",
    "category": "star",
    "ra_deg": 79.1723,
    "dec_deg": 45.9979,
    "magnitude": 0.08,
    "distance": "About 43 light-years",
    "description": "A multiple-star system in Auriga."
  },
  {
    "id": "rigel",
    "name": "Rigel",
    "category": "star",
    "ra_deg": 78.6345,
    "dec_deg": -8.2016,
    "magnitude": 0.13,
    "distance": "Roughly 860 light-years",
    "description": "A blue supergiant in Orion; brightness estimates vary."
  },
  {
    "id": "procyon",
    "name": "Procyon",
    "category": "star",
    "ra_deg": 114.8255,
    "dec_deg": 5.225,
    "magnitude": 0.34,
    "distance": "About 11.5 light-years",
    "description": "A nearby binary system in Canis Minor."
  },
  {
    "id": "betelgeuse",
    "name": "Betelgeuse",
    "category": "star",
    "ra_deg": 88.7929,
    "dec_deg": 7.4071,
    "magnitude": 0.5,
    "distance": "Uncertain; several hundred light-years",
    "description": "A variable red supergiant in Orion. Its listed magnitude is illustrative, not a current measurement."
  },
  {
    "id": "altair",
    "name": "Altair",
    "category": "star",
    "ra_deg": 297.6958,
    "dec_deg": 8.8683,
    "magnitude": 0.76,
    "distance": "About 17 light-years",
    "description": "A rapidly rotating star in Aquila and a corner of the Summer Triangle."
  },
  {
    "id": "aldebaran",
    "name": "Aldebaran",
    "category": "star",
    "ra_deg": 68.98,
    "dec_deg": 16.5093,
    "magnitude": 0.85,
    "distance": "About 65 light-years",
    "description": "An orange giant in Taurus, seen in the direction of the Hyades cluster."
  },
  {
    "id": "spica",
    "name": "Spica",
    "category": "star",
    "ra_deg": 201.2983,
    "dec_deg": -11.1613,
    "magnitude": 0.98,
    "distance": "About 250 light-years",
    "description": "A bright binary star in Virgo."
  },
  {
    "id": "antares",
    "name": "Antares",
    "category": "star",
    "ra_deg": 247.3519,
    "dec_deg": -26.432,
    "magnitude": 1.06,
    "distance": "Roughly 550 light-years",
    "description": "A variable red supergiant in Scorpius."
  },
  {
    "id": "pollux",
    "name": "Pollux",
    "category": "star",
    "ra_deg": 116.3289,
    "dec_deg": 28.0262,
    "magnitude": 1.14,
    "distance": "About 34 light-years",
    "description": "An orange giant in Gemini."
  },
  {
    "id": "fomalhaut",
    "name": "Fomalhaut",
    "category": "star",
    "ra_deg": 344.4128,
    "dec_deg": -29.6222,
    "magnitude": 1.16,
    "distance": "About 25 light-years",
    "description": "A bright star in Piscis Austrinus with a surrounding debris disk."
  },
  {
    "id": "deneb",
    "name": "Deneb",
    "category": "star",
    "ra_deg": 310.358,
    "dec_deg": 45.2803,
    "magnitude": 1.25,
    "distance": "Uncertain; thousands of light-years",
    "description": "A luminous supergiant in Cygnus and a corner of the Summer Triangle."
  },
  {
    "id": "regulus",
    "name": "Regulus",
    "category": "star",
    "ra_deg": 152.0929,
    "dec_deg": 11.9672,
    "magnitude": 1.35,
    "distance": "About 79 light-years",
    "description": "A bright multiple-star system in Leo."
  },
  {
    "id": "polaris",
    "name": "Polaris",
    "category": "star",
    "ra_deg": 37.9546,
    "dec_deg": 89.2641,
    "magnitude": 1.98,
    "distance": "Roughly 440 light-years",
    "description": "A variable star close to the north celestial pole. It is not exactly at the pole."
  },
  {
    "description": "A globular cluster with hundreds of thousands of stars.",
    "id": "M13",
    "category": "Cluster",
    "dec_deg": 36.4667,
    "ra_deg": 250.425,
    "name": "Hercules Cluster"
  },
  {
    "description": "A spiral galaxy in the Local Group.",
    "id": "M31",
    "category": "Galaxy",
    "dec_deg": 41.2667,
    "ra_deg": 10.6751,
    "name": "Andromeda Galaxy"
  },
  {
    "description": "A nearby region where new stars are forming.",
    "id": "M42",
    "category": "Nebula",
    "dec_deg": -5.45,
    "ra_deg": 83.85,
    "name": "Orion Nebula"
  },
  {
    "description": "A group of young stars also called the Seven Sisters.",
    "id": "M45",
    "category": "Cluster",
    "dec_deg": 24.1167,
    "ra_deg": 56.75,
    "name": "Pleiades"
  }
];
