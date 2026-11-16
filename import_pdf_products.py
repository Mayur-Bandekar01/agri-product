#!/usr/bin/env python3
"""
Import 110 Products from PDF to Database
Clears existing data and imports fresh product list
"""

import sys
import os
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database.connection import SessionLocal, engine
from app.models import Product, User, Farmer, Invoice, InvoiceItem, Payment, StockMovement, ProductPriceHistory
from sqlalchemy import text

# Product data from PDF (110 products across 4 pages)
PRODUCTS_DATA = [
    # Page 1: Products 1-35
    {"sl": 1, "name": "Tata Metri (250 Gm)", "hsn": "38089390", "gst": 18, "qty": 20, "rate_incl": 335.00, "rate_excl": 283.90, "unit": "NOS", "disc": 0, "selling": 450},
    {"sl": 2, "name": "Burn Out (1 Ltr)", "hsn": "38089390", "gst": 18, "qty": 30, "rate_incl": 350.00, "rate_excl": 296.61, "unit": "BOTTOL", "disc": 0, "selling": 400},
    {"sl": 3, "name": "Plasto (250 Gm)", "hsn": "38089110", "gst": 18, "qty": 20, "rate_incl": 310.00, "rate_excl": 262.71, "unit": "NOS", "disc": 0, "selling": 1000},
    {"sl": 4, "name": "Salix (500 Gm)", "hsn": "38089320", "gst": 18, "qty": 40, "rate_incl": 188.00, "rate_excl": 159.32, "unit": "Packets", "disc": 0, "selling": 200},
    {"sl": 5, "name": "Tynzer (30 Ml)", "hsn": "38089390", "gst": 18, "qty": 10, "rate_incl": 1175.00, "rate_excl": 995.76, "unit": "NOS", "disc": 0, "selling": 1200},
    {"sl": 6, "name": "Terrox (IIL) 30 Ml", "hsn": "38089390", "gst": 18, "qty": 5, "rate_incl": 550.00, "rate_excl": 466.10, "unit": "NOS", "disc": 0, "selling": 1000},
    {"sl": 7, "name": "Strike (IIL) 500 Gm", "hsn": "38089390", "gst": 18, "qty": 5, "rate_incl": 218.01, "rate_excl": 184.75, "unit": "NOS", "disc": 0, "selling": 250},
    {"sl": 8, "name": "Terrox (IIL) 15 Ml", "hsn": "38089390", "gst": 18, "qty": 3, "rate_incl": 293.01, "rate_excl": 248.31, "unit": "NOS", "disc": 0, "selling": 300},
    {"sl": 9, "name": "Strike (IIL) 250 Gm", "hsn": "38089390", "gst": 18, "qty": 3, "rate_incl": 115.00, "rate_excl": 97.46, "unit": "NOS", "disc": 0, "selling": 600},
    {"sl": 10, "name": "Vesnite Complete (1 Ltr)", "hsn": "38089390", "gst": 18, "qty": 6, "rate_incl": 1616.00, "rate_excl": 1369.49, "unit": "NOS", "disc": 0, "selling": 1300},
    {"sl": 11, "name": "Nakshtra (IIL) 1250 Gms", "hsn": "38089390", "gst": 18, "qty": 8, "rate_incl": 725.00, "rate_excl": 614.41, "unit": "NOS", "disc": 0, "selling": 900},
    {"sl": 12, "name": "Atrataf (TATA) 500 Gm", "hsn": "38089390", "gst": 18, "qty": 20, "rate_incl": 220.00, "rate_excl": 186.44, "unit": "NOS", "disc": 0, "selling": 250},
    {"sl": 13, "name": "Strike (IIL) 500 Gm", "hsn": "38089390", "gst": 18, "qty": 10, "rate_incl": 218.01, "rate_excl": 184.75, "unit": "NOS", "disc": 0, "selling": 230},
    {"sl": 14, "name": "Weedout (JU) 1 Ltr", "hsn": "38089390", "gst": 18, "qty": 10, "rate_incl": 335.00, "rate_excl": 283.90, "unit": "NOS", "disc": 0, "selling": 400},
    {"sl": 15, "name": "Oxykill (250 Ml)", "hsn": "38089390", "gst": 18, "qty": 5, "rate_incl": 370.00, "rate_excl": 313.56, "unit": "BOTTOL", "disc": 0, "selling": 440},
    {"sl": 16, "name": "Oxykill (100 Ml)", "hsn": "38089350", "gst": 18, "qty": 5, "rate_incl": 155.00, "rate_excl": 131.36, "unit": "BOTTOL", "disc": 0, "selling": 220},
    {"sl": 17, "name": "Sweep Power (1 Ltr)", "hsn": "38089390", "gst": 18, "qty": 4, "rate_incl": 740.00, "rate_excl": 627.12, "unit": "BOTTOL", "disc": 0, "selling": 850},
    {"sl": 18, "name": "Sindica (Atul) 1 Kg", "hsn": "38089390", "gst": 18, "qty": 5, "rate_incl": 1356.00, "rate_excl": 1149.15, "unit": "NOS", "disc": 0, "selling": 1400},
    {"sl": 19, "name": "Triskele (1.2 Kg)", "hsn": "38089390", "gst": 18, "qty": 5, "rate_incl": 1670.00, "rate_excl": 1415.25, "unit": "NOS", "disc": 0, "selling": 1700},
    {"sl": 20, "name": "Topper 77 (100 Gm)", "hsn": "38089350", "gst": 18, "qty": 100, "rate_incl": 62.00, "rate_excl": 52.54, "unit": "Packets", "disc": 0, "selling": 80},
    {"sl": 21, "name": "Sempra (36 Gms)", "hsn": "38089350", "gst": 18, "qty": 5, "rate_incl": 1348.00, "rate_excl": 1142.37, "unit": "Packets", "disc": 0, "selling": 1350},
    {"sl": 22, "name": "Sempra (18 Gm)", "hsn": "38089350", "gst": 18, "qty": 4, "rate_incl": 776.00, "rate_excl": 657.63, "unit": "Packets", "disc": 0, "selling": 800},
    {"sl": 23, "name": "Sempra (3.6 Gm)", "hsn": "38089350", "gst": 18, "qty": 10, "rate_incl": 206.00, "rate_excl": 174.58, "unit": "Packets", "disc": 0, "selling": 210},
    {"sl": 24, "name": "Tata Metri (100 Gm)", "hsn": "38089350", "gst": 18, "qty": 10, "rate_incl": 145.00, "rate_excl": 122.88, "unit": "NOS", "disc": 0, "selling": 200},
    {"sl": 25, "name": "Pump EB-20 Double Motor", "hsn": "84248200", "gst": 5, "qty": 1, "rate_incl": 3250.00, "rate_excl": 3095.24, "unit": "NOS", "disc": 0, "selling": 3500},
    {"sl": 26, "name": "Neptune Lithium (12*24) 20 Ltr Pump", "hsn": "84244900", "gst": 5, "qty": 1, "rate_incl": 3250.00, "rate_excl": 3095.24, "unit": "NOS", "disc": 0, "selling": 3500},
    {"sl": 27, "name": "M45 (Dhanuka) 250 Gm", "hsn": "38089290", "gst": 18, "qty": 10, "rate_incl": 136.00, "rate_excl": 115.25, "unit": "Packets", "disc": 0, "selling": 180},
    {"sl": 28, "name": "M45 (Dhanuka) 100 Gm", "hsn": "38089290", "gst": 18, "qty": 5, "rate_incl": 58.00, "rate_excl": 49.15, "unit": "Packets", "disc": 0, "selling": 100},
    {"sl": 29, "name": "Saaf (500 Gm)", "hsn": "38089290", "gst": 18, "qty": 10, "rate_incl": 370.00, "rate_excl": 313.56, "unit": "Packets", "disc": 0, "selling": 420},
    {"sl": 30, "name": "Saaf (250 Gm)", "hsn": "38089290", "gst": 18, "qty": 10, "rate_incl": 195.00, "rate_excl": 165.25, "unit": "NOS", "disc": 0, "selling": 220},
    {"sl": 31, "name": "Saaf (100 Gm)", "hsn": "38089290", "gst": 18, "qty": 10, "rate_incl": 80.00, "rate_excl": 67.80, "unit": "Packets", "disc": 0, "selling": 100},
    {"sl": 32, "name": "Sixer (Dhanuka) 250 Gm", "hsn": "38089290", "gst": 18, "qty": 5, "rate_incl": 190.00, "rate_excl": 161.02, "unit": "Packets", "disc": 0, "selling": 220},
    {"sl": 33, "name": "Sixer (Dhanuka) 100 Gm", "hsn": "38089290", "gst": 18, "qty": 5, "rate_incl": 80.00, "rate_excl": 67.80, "unit": "Packets", "disc": 0, "selling": 160},
    {"sl": 34, "name": "RidomilGold (250 Gm)", "hsn": "38089290", "gst": 18, "qty": 2, "rate_incl": 359.99, "rate_excl": 305.08, "unit": "Packets", "disc": 0, "selling": 480},
    {"sl": 35, "name": "Contaf (1 Ltr)", "hsn": "38089290", "gst": 18, "qty": 5, "rate_incl": 590.00, "rate_excl": 500.00, "unit": "BOTTOL", "disc": 0, "selling": 650},
    
    # Page 2: Products 36-67
    {"sl": 36, "name": "Contaf (500 Ml)", "hsn": "38089290", "gst": 18, "qty": 10, "rate_incl": 310.00, "rate_excl": 262.71, "unit": "BOTTOL", "disc": 0, "selling": 360},
    {"sl": 37, "name": "Contaf (250 Ml)", "hsn": "38089290", "gst": 18, "qty": 10, "rate_incl": 165.00, "rate_excl": 139.83, "unit": "BOTTOL", "disc": 0, "selling": 180},
    {"sl": 38, "name": "Contaf (100 Ml)", "hsn": "38089290", "gst": 18, "qty": 5, "rate_incl": 80.00, "rate_excl": 67.80, "unit": "NOS", "disc": 0, "selling": 80},
    {"sl": 39, "name": "Lethal Gr (IIL) 1 Kg", "hsn": "38089199", "gst": 18, "qty": 10, "rate_incl": 127.99, "rate_excl": 108.47, "unit": "NOS", "disc": 0, "selling": 160},
    {"sl": 40, "name": "Bilbo B-505 (Bharat Certis) 1 Ltr", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 660.00, "rate_excl": 559.32, "unit": "NOS", "disc": 0, "selling": 750},
    {"sl": 41, "name": "Bilbo B-505 (Bharat Certis) 500 Ml", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 359.99, "rate_excl": 305.08, "unit": "NOS", "disc": 0, "selling": 380},
    {"sl": 42, "name": "Karate (1 Ltr)", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 610.00, "rate_excl": 516.95, "unit": "BOTTOL", "disc": 0, "selling": 650},
    {"sl": 43, "name": "Karate (500 Ml)", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 315.00, "rate_excl": 266.95, "unit": "BOTTOL", "disc": 0, "selling": 380},
    {"sl": 44, "name": "Karate (250 Ml)", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 165.00, "rate_excl": 139.83, "unit": "BOTTOL", "disc": 0, "selling": 180},
    {"sl": 45, "name": "Tafgor (250 Ml)", "hsn": "38089123", "gst": 18, "qty": 5, "rate_incl": 188.00, "rate_excl": 159.32, "unit": "NOS", "disc": 0, "selling": 280},
    {"sl": 46, "name": "Tafgor (100 Ml)", "hsn": "38089123", "gst": 18, "qty": 5, "rate_incl": 80.00, "rate_excl": 67.80, "unit": "BOTTOL", "disc": 0, "selling": 120},
    {"sl": 47, "name": "Dhanulux (250 Ml)", "hsn": "38089132", "gst": 18, "qty": 5, "rate_incl": 178.00, "rate_excl": 150.85, "unit": "BOTTOL", "disc": 0, "selling": 200},
    {"sl": 48, "name": "Dhanusan (100 Ml)", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 127.99, "rate_excl": 108.47, "unit": "BOTTOL", "disc": 0, "selling": 120},
    {"sl": 49, "name": "Coragen (150 Ml)", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 1010.00, "rate_excl": 855.93, "unit": "BOTTOL", "disc": 0, "selling": 1050},
    {"sl": 50, "name": "Coragen (60 Ml)", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 424.00, "rate_excl": 359.32, "unit": "BOTTOL", "disc": 0, "selling": 450},
    {"sl": 51, "name": "Coragen (30 Ml)", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 226.01, "rate_excl": 191.53, "unit": "BOTTOL", "disc": 0, "selling": 280},
    {"sl": 52, "name": "Asataf (100 Gm)", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 90.00, "rate_excl": 76.27, "unit": "NOS", "disc": 0, "selling": 170},
    {"sl": 53, "name": "Asataf (250 Gm)", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 210.00, "rate_excl": 177.97, "unit": "Packets", "disc": 0, "selling": 280},
    {"sl": 54, "name": "Lesenta (100 Gm)", "hsn": "38089199", "gst": 18, "qty": 10, "rate_incl": 949.99, "rate_excl": 805.08, "unit": "Packets", "disc": 0, "selling": 1000},
    {"sl": 55, "name": "Spolit (100 Gm)", "hsn": "38089199", "gst": 18, "qty": 6, "rate_incl": 140.00, "rate_excl": 118.64, "unit": "BOTTOL", "disc": 0, "selling": 200},
    {"sl": 56, "name": "EM 1 (Dhanuka) 100 Gm", "hsn": "38089199", "gst": 18, "qty": 4, "rate_incl": 210.00, "rate_excl": 177.97, "unit": "NOS", "disc": 0, "selling": 250},
    {"sl": 57, "name": "EM 1 (Dhanuka) 50 Gm", "hsn": "38089199", "gst": 18, "qty": 10, "rate_incl": 110.00, "rate_excl": 93.22, "unit": "NOS", "disc": 0, "selling": 150},
    {"sl": 58, "name": "Lethal (IIL) 1 Ltr", "hsn": "38089199", "gst": 18, "qty": 10, "rate_incl": 340.01, "rate_excl": 288.14, "unit": "NOS", "disc": 0, "selling": 360},
    {"sl": 59, "name": "Lethal (IIL) 500 Ml", "hsn": "38089199", "gst": 18, "qty": 20, "rate_incl": 178.99, "rate_excl": 151.69, "unit": "NOS", "disc": 0, "selling": 200},
    {"sl": 60, "name": "Lethal (IIL) 250 Ml)", "hsn": "38089199", "gst": 18, "qty": 20, "rate_incl": 97.00, "rate_excl": 82.20, "unit": "NOS", "disc": 0, "selling": 110},
    {"sl": 61, "name": "Lethal (IIL) 100 Ml", "hsn": "38089199", "gst": 18, "qty": 10, "rate_incl": 44.00, "rate_excl": 37.29, "unit": "NOS", "disc": 0, "selling": 50},
    {"sl": 62, "name": "Media (IMIDACLOPRID) 100 Ml", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 115.00, "rate_excl": 97.46, "unit": "BOTTOL", "disc": 0, "selling": 220},
    {"sl": 63, "name": "Media (IMIDACLOPRID) 50 Ml", "hsn": "38089199", "gst": 18, "qty": 5, "rate_incl": 70.00, "rate_excl": 59.32, "unit": "BOTTOL", "disc": 0, "selling": 110},
    {"sl": 64, "name": "P-Attract (100 Ml) Pratik", "hsn": "38089340", "gst": 18, "qty": 5, "rate_incl": 40.00, "rate_excl": 33.90, "unit": "NOS", "disc": 0, "selling": 50},
    {"sl": 65, "name": "P-Attract (250 Ml) Pratik", "hsn": "38089340", "gst": 18, "qty": 5, "rate_incl": 80.00, "rate_excl": 67.80, "unit": "NOS", "disc": 0, "selling": 100},
    {"sl": 66, "name": "Gold Mine (GPC) 500 Ml", "hsn": "38083030", "gst": 5, "qty": 20, "rate_incl": 150.00, "rate_excl": 142.86, "unit": "NOS", "disc": 0, "selling": 280},
    {"sl": 67, "name": "Nutrol Effect (250 Gm) Pratik", "hsn": "28332910", "gst": 5, "qty": 10, "rate_incl": 170.00, "rate_excl": 161.90, "unit": "NOS", "disc": 0, "selling": 280},
    
    # Page 3: Products 68-95
    {"sl": 68, "name": "Grand Silicon Powder (100 Gm)", "hsn": "38089340", "gst": 18, "qty": 5, "rate_incl": 90.00, "rate_excl": 76.27, "unit": "NOS", "disc": 0, "selling": 180},
    {"sl": 69, "name": "Grand Humic (Pratik) 500 Gm", "hsn": "38089340", "gst": 18, "qty": 10, "rate_incl": 100.01, "rate_excl": 84.75, "unit": "NOS", "disc": 0, "selling": 250},
    {"sl": 70, "name": "Boron 20% (Aries) 500 Gm", "hsn": "28401900", "gst": 5, "qty": 5, "rate_incl": 210.00, "rate_excl": 200.00, "unit": "Packets", "disc": 0, "selling": 260},
    {"sl": 71, "name": "Boron 20% (Aries) 250 Gm", "hsn": "28401900", "gst": 5, "qty": 5, "rate_incl": 100.00, "rate_excl": 95.24, "unit": "Packets", "disc": 0, "selling": 140},
    {"sl": 72, "name": "Agromin Max (1 Kg)", "hsn": "28332990", "gst": 5, "qty": 5, "rate_incl": 410.00, "rate_excl": 390.48, "unit": "NOS", "disc": 0, "selling": 680},
    {"sl": 73, "name": "Agromin Max (500 Gm)", "hsn": "28332990", "gst": 5, "qty": 5, "rate_incl": 235.00, "rate_excl": 223.81, "unit": "Packets", "disc": 0, "selling": 380},
    {"sl": 74, "name": "Agromin Max (250 Gm)", "hsn": "28332990", "gst": 5, "qty": 10, "rate_incl": 125.00, "rate_excl": 119.05, "unit": "Packets", "disc": 0, "selling": 220},
    {"sl": 75, "name": "Agripro Plus (250 Gm)", "hsn": "31059090", "gst": 5, "qty": 10, "rate_incl": 256.00, "rate_excl": 243.81, "unit": "Packets", "disc": 0, "selling": 350},
    {"sl": 76, "name": "Quantis (400 Ml)", "hsn": "31059090", "gst": 5, "qty": 5, "rate_incl": 330.00, "rate_excl": 314.29, "unit": "NOS", "disc": 0, "selling": 400},
    {"sl": 77, "name": "Isabion (1 Ltr)", "hsn": "31010099", "gst": 5, "qty": 3, "rate_incl": 1080.00, "rate_excl": 1028.57, "unit": "NOS", "disc": 0, "selling": 1200},
    {"sl": 78, "name": "Tata Bahar (500 Ml)", "hsn": "31010099", "gst": 5, "qty": 4, "rate_incl": 335.00, "rate_excl": 319.05, "unit": "NOS", "disc": 0, "selling": 450},
    {"sl": 79, "name": "Hoshi (250 Ml)", "hsn": "38089330", "gst": 5, "qty": 10, "rate_incl": 142.00, "rate_excl": 135.24, "unit": "BOTTOL", "disc": 0, "selling": 170},
    {"sl": 80, "name": "Nano DAP (500 Ml)", "hsn": "31051000", "gst": 5, "qty": 5, "rate_incl": 560.00, "rate_excl": 533.33, "unit": "NOS", "disc": 0, "selling": 600},
    {"sl": 81, "name": "Jivras (1 Ltr)", "hsn": "28332990", "gst": 5, "qty": 5, "rate_incl": 535.00, "rate_excl": 509.52, "unit": "BOTTOL", "disc": 0, "selling": 600},
    {"sl": 82, "name": "Jivras (500 Ml)", "hsn": "28332990", "gst": 5, "qty": 5, "rate_incl": 330.00, "rate_excl": 314.29, "unit": "BOTTOL", "disc": 0, "selling": 330},
    {"sl": 83, "name": "Horse Power (GPC) 500 Gm", "hsn": "310100", "gst": 5, "qty": 30, "rate_incl": 150.00, "rate_excl": 142.86, "unit": "NOS", "disc": 0, "selling": 250},
    {"sl": 84, "name": "Magnesium Sulphate (Pratik) 1 Kg", "hsn": "28332910", "gst": 5, "qty": 10, "rate_incl": 55.00, "rate_excl": 52.38, "unit": "NOS", "disc": 0, "selling": 60},
    {"sl": 85, "name": "IBA 1 Gm", "hsn": "29339990", "gst": 18, "qty": 25, "rate_incl": 20.00, "rate_excl": 16.95, "unit": "NOS", "disc": 0, "selling": 40},
    {"sl": 86, "name": "IBA (5 Gm)", "hsn": "29339900", "gst": 18, "qty": 10, "rate_incl": 90.00, "rate_excl": 76.27, "unit": "NOS", "disc": 0, "selling": 180},
    {"sl": 87, "name": "6 BA (1 Gm)", "hsn": "38089340", "gst": 18, "qty": 25, "rate_incl": 20.00, "rate_excl": 16.95, "unit": "NOS", "disc": 0, "selling": 110},
    {"sl": 88, "name": "6 BA (5 Gm)", "hsn": "38089340", "gst": 18, "qty": 10, "rate_incl": 90.00, "rate_excl": 76.27, "unit": "NOS", "disc": 0, "selling": 180},
    {"sl": 89, "name": "Magnesium Sulphate Criyagen (25 Kg)", "hsn": "28332100", "gst": 5, "qty": 60, "rate_incl": 740.00, "rate_excl": 704.76, "unit": "NOS", "disc": 0, "selling": 250},
    {"sl": 90, "name": "Magnesium Sulphate Criyagen (50 Kg)", "hsn": "28332100", "gst": 5, "qty": 10, "rate_incl": 1460.00, "rate_excl": 1390.48, "unit": "Bags", "disc": 0, "selling": 1550},
    {"sl": 91, "name": "Bio Power Gold (10 Kg)", "hsn": "31010099", "gst": 5, "qty": 5, "rate_incl": 1120.00, "rate_excl": 1066.67, "unit": "NOS", "disc": 0, "selling": 1200},
    {"sl": 92, "name": "BIURON (Bharat Certis) 500 Gm", "hsn": "38089390", "gst": 18, "qty": 10, "rate_incl": 400.00, "rate_excl": 338.98, "unit": "NOS", "disc": 0, "selling": 450},
    {"sl": 93, "name": "Biozyme Crop+ (1 Ltr)", "hsn": "31059010", "gst": 5, "qty": 5, "rate_incl": 730.00, "rate_excl": 695.24, "unit": "BOTTOL", "disc": 0, "selling": 780},
    {"sl": 94, "name": "Biozyme Crop+ (500 Ml)", "hsn": "31059010", "gst": 5, "qty": 5, "rate_incl": 430.00, "rate_excl": 409.52, "unit": "BOTTOL", "disc": 0, "selling": 450},
    {"sl": 95, "name": "Biozyme Crop+ (250 Ml)", "hsn": "31010099", "gst": 5, "qty": 5, "rate_incl": 220.00, "rate_excl": 209.52, "unit": "NOS", "disc": 0, "selling": 250},
    
    # Page 4: Products 96-110
    {"sl": 96, "name": "Biovita (500 Ml)", "hsn": "31059010", "gst": 5, "qty": 5, "rate_incl": 390.00, "rate_excl": 371.43, "unit": "BOTTOL", "disc": 0, "selling": 480},
    {"sl": 97, "name": "Agromin (1 Ltr)", "hsn": "28332990", "gst": 5, "qty": 12, "rate_incl": 290.00, "rate_excl": 276.19, "unit": "BOTTOL", "disc": 0, "selling": 360},
    {"sl": 98, "name": "Agromin (500 Ml)", "hsn": "28332990", "gst": 5, "qty": 20, "rate_incl": 160.00, "rate_excl": 152.38, "unit": "BOTTOL", "disc": 0, "selling": 220},
    {"sl": 99, "name": "Agromin (250 Ml)", "hsn": "28332990", "gst": 5, "qty": 10, "rate_incl": 90.00, "rate_excl": 85.71, "unit": "BOTTOL", "disc": 0, "selling": 100},
    {"sl": 100, "name": "Progibb (1 Gm)", "hsn": "38089330", "gst": 5, "qty": 25, "rate_incl": 50.00, "rate_excl": 47.62, "unit": "NOS", "disc": 0, "selling": 60},
    {"sl": 101, "name": "Progibb (5 Gm)", "hsn": "38089330", "gst": 5, "qty": 25, "rate_incl": 280.00, "rate_excl": 266.67, "unit": "NOS", "disc": 0, "selling": 280},
    {"sl": 102, "name": "Combical + (Aries) 1 Kg", "hsn": "31059090", "gst": 5, "qty": 10, "rate_incl": 195.00, "rate_excl": 185.71, "unit": "Packets", "disc": 0, "selling": 220},
    {"sl": 103, "name": "13:00:45 (DCM) 1 Kg", "hsn": "31059010", "gst": 5, "qty": 30, "rate_incl": 160.00, "rate_excl": 152.38, "unit": "NOS", "disc": 0, "selling": 170},
    {"sl": 104, "name": "19:19:19 (Mahadhan) 1 Kg", "hsn": "31051000", "gst": 5, "qty": 25, "rate_incl": 145.01, "rate_excl": 138.10, "unit": "NOS", "disc": 0, "selling": 160},
    {"sl": 105, "name": "12:61:00 (Mahadhan) 1 Kg", "hsn": "31054000", "gst": 5, "qty": 25, "rate_incl": 195.00, "rate_excl": 185.71, "unit": "NOS", "disc": 0, "selling": 220},
    {"sl": 106, "name": "24:24:00 (Mahadhan) 1 Kg Smart", "hsn": "31055100", "gst": 5, "qty": 25, "rate_incl": 170.00, "rate_excl": 161.90, "unit": "NOS", "disc": 0, "selling": 180},
    {"sl": 107, "name": "13:40:13 (Mahadhan) 1 Kg", "hsn": "31052000", "gst": 5, "qty": 25, "rate_incl": 185.00, "rate_excl": 176.19, "unit": "Packets", "disc": 0, "selling": 220},
    {"sl": 108, "name": "00:52:34 (Mahadhan) 1 Kg", "hsn": "31056000", "gst": 5, "qty": 25, "rate_incl": 243.00, "rate_excl": 231.43, "unit": "Packets", "disc": 0, "selling": 250},
    {"sl": 109, "name": "Calcium Nitrate (Mahadhan) 1 Kg", "hsn": "31056000", "gst": 5, "qty": 25, "rate_incl": 85.00, "rate_excl": 80.95, "unit": "NOS", "disc": 0, "selling": 110},
    {"sl": 110, "name": "Agromin Soil Appl. (10 Kg)", "hsn": "28332990", "gst": 5, "qty": 5, "rate_incl": 520.00, "rate_excl": 495.24, "unit": "Bags", "disc": 0, "selling": 700},
]

def clear_all_data(db):
    """Clear all existing data from database"""
    print("\n🗑️  Clearing existing data...")
    
    try:
        # Disable foreign key constraints temporarily
        db.execute(text("PRAGMA foreign_keys = OFF"))
        db.commit()
        
        # Delete in proper order (respecting foreign keys)
        tables_to_clear = [
            ('invoice_items', InvoiceItem),
            ('payments', Payment),
            ('invoices', Invoice),
            ('stock_movements', StockMovement),
            ('product_price_history', ProductPriceHistory),
            ('products', Product),
            ('farmers', Farmer),
            # Keep User table - don't delete admin accounts
        ]
        
        for table_name, table_model in tables_to_clear:
            try:
                count = db.query(table_model).count()
                if count > 0:
                    db.query(table_model).delete()
                    print(f"  ✅ Deleted {count} records from {table_name}")
                else:
                    print(f"  ⏭️  {table_name} already empty")
            except Exception as e:
                print(f"  ⚠️  Skipping {table_name}: {str(e)}")
        
        db.commit()
        
        # Re-enable foreign key constraints
        db.execute(text("PRAGMA foreign_keys = ON"))
        db.commit()
        
        print("✅ All existing data cleared successfully!\n")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Error clearing data: {e}")
        import traceback
        traceback.print_exc()
        return False

def determine_category(name, hsn):
    """Determine product category based on name and HSN code"""
    name_lower = name.lower()
    
    # Fertilizers
    fertilizer_keywords = ['dap', 'npk', 'urea', 'potash', 'nitrogen', 'phosphate', 
                          'sulphate', 'nitrate', 'boron', 'magnesium', 'calcium',
                          'agromin', 'combical', 'mahadhan', 'dcm']
    if any(kw in name_lower for kw in fertilizer_keywords):
        return "Fertilizer"
    
    # Equipment
    if 'pump' in name_lower or 'motor' in name_lower:
        return "Equipment"
    
    # Bio-stimulants
    bio_keywords = ['bio', 'isabion', 'biozyme', 'jivras', 'humic', 'silicon',
                   'horse power', 'quantis', 'agripro', 'bahar', 'hoshi']
    if any(kw in name_lower for kw in bio_keywords):
        return "Bio-Stimulant"
    
    # Default to Pesticides for agricultural chemicals
    return "Pesticides"

def import_products(db):
    """Import all 110 products from PDF data"""
    print("📦 Importing 110 products from PDF...\n")
    
    imported = 0
    errors = []
    
    for product_data in PRODUCTS_DATA:
        try:
            # Calculate GST component
            gst_component = Decimal(str(product_data['rate_incl'])) - Decimal(str(product_data['rate_excl']))
            
            # Generate SKU
            sku = f"PROD-{product_data['sl']:03d}"
            
            # Determine category
            category = determine_category(product_data['name'], product_data['hsn'])
            
            # Create product
            product = Product(
                name=product_data['name'],
                sku=sku,
                category=category,
                unit=product_data['unit'],
                hsn_code=product_data['hsn'],
                gst_rate=Decimal(str(product_data['gst'])),
                purchase_price_including_gst=Decimal(str(product_data['rate_incl'])),
                purchase_price_excluding_gst=Decimal(str(product_data['rate_excl'])),
                purchase_gst_component=gst_component,
                selling_price=Decimal(str(product_data['selling'])),
                discount_percentage=Decimal(str(product_data['disc'])),
                stock=Decimal(str(product_data['qty'])),
                initial_quantity=Decimal(str(product_data['qty'])),
                min_stock=Decimal('5'),  # Default minimum stock
                gst_selection_type='preset' if product_data['gst'] in [5, 12, 18, 28] else 'custom',
                selling_price_tax_mode='exclusive',
                is_active=True,
                source_reference='PDF Import - typed_invoice_110_products_with_selling_price_column-1.pdf'
            )
            
            db.add(product)
            imported += 1
            
            if imported % 10 == 0:
                print(f"  ✅ Imported {imported}/110 products...")
                
        except Exception as e:
            errors.append(f"Product {product_data['sl']}: {str(e)}")
    
    try:
        db.commit()
        print(f"\n✅ Successfully imported {imported} products!")
        
        if errors:
            print(f"\n⚠️  {len(errors)} errors encountered:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        return imported
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error committing products: {e}")
        return 0

def verify_import(db):
    """Verify the import was successful"""
    print("\n🔍 Verifying import...\n")
    
    # Count products
    total_products = db.query(Product).count()
    print(f"  📊 Total products in database: {total_products}")
    
    # Check HSN codes
    products_with_hsn = db.query(Product).filter(Product.hsn_code.isnot(None)).count()
    print(f"  📋 Products with HSN codes: {products_with_hsn}")
    
    # Check categories
    categories = db.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    print(f"\n  📂 Products by category:")
    for cat, count in categories:
        print(f"     - {cat}: {count} products")
    
    # Check stock value
    total_stock_value = db.query(
        func.sum(Product.stock * Product.purchase_price_excluding_gst)
    ).scalar() or 0
    print(f"\n  💰 Total stock value: ₹{float(total_stock_value):,.2f}")
    
    # Sample products
    print(f"\n  📝 Sample products:")
    samples = db.query(Product).limit(5).all()
    for p in samples:
        print(f"     {p.sku}: {p.name} (HSN: {p.hsn_code}, Stock: {p.stock} {p.unit})")
    
    return total_products == 110

def main():
    """Main import function"""
    print("\n" + "="*70)
    print("  PDF PRODUCT IMPORT - 110 Products")
    print("="*70)
    print("\nThis will:")
    print("  1. Clear ALL existing data (products, invoices, payments, etc.)")
    print("  2. Import 110 products from PDF")
    print("  3. Set initial stock quantities")
    print("  4. Add HSN codes and GST rates")
    print("\n⚠️  WARNING: This will DELETE all existing data!")
    print("    Users/admins will NOT be deleted (login preserved)")
    print("\n" + "="*70)
    
    # Check for --force argument
    if '--force' in sys.argv:
        print("\n✅ --force flag detected, proceeding without confirmation...")
        response = 'yes'
    else:
        response = input("\nAre you sure you want to proceed? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("\n❌ Import cancelled.")
        return 1
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Step 1: Clear existing data
        if not clear_all_data(db):
            print("\n❌ Failed to clear data. Aborting.")
            return 1
        
        # Step 2: Import products
        imported_count = import_products(db)
        
        if imported_count == 0:
            print("\n❌ No products imported. Check errors above.")
            return 1
        
        # Step 3: Verify import
        if verify_import(db):
            print("\n" + "="*70)
            print("  ✅ IMPORT COMPLETE!")
            print("="*70)
            print(f"\n  Successfully imported {imported_count} products from PDF")
            print("  Database is now ready with fresh data")
            print("\n  Next steps:")
            print("    1. Start backend: cd backend && venv\\Scripts\\activate && python -m uvicorn app.main:app --reload")
            print("    2. Login to application")
            print("    3. View Products page - you should see all 110 products")
            print("    4. Check HSN codes in CA Export")
            print("\n" + "="*70 + "\n")
            return 0
        else:
            print("\n⚠️  Import verification failed. Check data manually.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == '__main__':
    # Import sqlalchemy func for verification
    from sqlalchemy import func
    sys.exit(main())
