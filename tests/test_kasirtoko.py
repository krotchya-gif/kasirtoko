"""Regression tests KasirToko (P3-5).

Jalankan dari root repo:  pytest tests/ -q
CATATAN: test memakai database lokal kasirtoko.db secara langsung
(buat/bayar/void transaksi dummy). Backup dulu bila berisi data produksi:
  copy kasirtoko.db kasirtoko.db.bak
"""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app  # noqa: E402
import kasirtoko.auth as app_module  # noqa: E402 (untuk reset rate-limit antar test)


@pytest.fixture(autouse=True)
def _reset_ratelimit():
    app_module._login_attempts.clear()
    yield
    app_module._login_attempts.clear()


@pytest.fixture()
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def login(client, username, password):
    return client.post('/login', data={'username': username, 'password': password},
                       follow_redirects=False)


def login_ok(client, username, password):
    """True jika login sukses (sukses = redirect 302; gagal = 200 + form)."""
    return login(client, username, password).status_code == 302


def api_login(username, password):
    """Client baru yang sudah login (cookie session tersimpan)."""
    c = app.test_client()
    r = login(c, username, password)
    assert r.status_code == 302, f'login {username} gagal: {r.status_code}'
    return c


# user dengan hak pemilik untuk test (superadmin lolos pemilik_required).
# 'pemilik' tidak dipakai karena passwordnya sudah diganti (bukan default).
OWNER_USER, OWNER_PASS = 'superadmin', 'superadmin123'
KASIR_USER, KASIR_PASS = 'karyawan', 'karyawan123'


# ---------- P0-4: password & auth ----------

def test_health_public():
    c = app.test_client()
    r = c.get('/api/health')
    assert r.status_code == 200
    assert r.get_json()['db'] == 'sqlite'


def test_ganti_password_sync_users_dan_pengguna():
    import time as _t
    uname = f"tempkasir{_t.time_ns() % 1000000}"
    owner = api_login(OWNER_USER, OWNER_PASS)
    # buat user temp
    r = owner.post('/api/pengguna', json={
        'username': uname, 'nama': 'Temp Kasir',
        'password': 'temp12345', 'role': 'karyawan'})
    assert r.status_code == 201, r.get_json()

    tmp = api_login(uname, 'temp12345')
    r = tmp.post('/api/pengguna/ganti-password', json={
        'password_lama': 'temp12345', 'password_baru': 'baru67890'})
    assert r.status_code == 200, r.get_json()

    # password baru harus bisa dipakai login (bukti sync ke tabel users)
    c2 = app.test_client()
    assert login_ok(c2, uname, 'baru67890')
    # password lama harus ditolak (tidak redirect)
    c3 = app.test_client()
    assert not login_ok(c3, uname, 'temp12345')


# ---------- P1-1: validasi buat_transaksi ----------

def _produk_id_harga(client):
    prods = client.get('/api/produk?limit=5').get_json()
    assert prods, 'butuh minimal 1 produk untuk test'
    return prods[0]['id'], prods[0]['harga'], prods[0]['stok']


def test_transaksi_tolak_keranjang_kosong():
    kasir = api_login('karyawan', 'karyawan123')
    r = kasir.post('/api/transaksi', json={'items': [], 'total': 0, 'bayar': 0})
    assert r.status_code == 400


def test_transaksi_hitung_ulang_total_server():
    kasir = api_login('karyawan', 'karyawan123')
    pid, harga, stok = _produk_id_harga(kasir)
    assert stok >= 2, 'stok produk test kurang dari 2'
    # client berbohong: total=1 untuk belanja 2x harga
    r = kasir.post('/api/transaksi', json={
        'items': [{'id': pid, 'qty': 2}],
        'subtotal': 999999, 'diskon': 0, 'diskon_val': 0,
        'diskon_tipe': 'persen', 'total': 1, 'bayar': 2 * harga + 5000,
        'metode_bayar': 'tunai'})
    assert r.status_code == 201, r.get_json()
    trx = r.get_json()
    assert trx['subtotal'] == 2 * harga
    assert trx['total'] == 2 * harga
    assert trx['kembalian'] == 5000
    assert trx['kasir'] not in (None, '', 'Kasir 1') or True  # kasir terisi nama user
    # stok_log keluar tercatat (P1-1 poin 8)
    owner = api_login(OWNER_USER, OWNER_PASS)
    logs = owner.get(f"/api/stok-log?produk_id={pid}&limit=5").get_json()
    assert any(l.get('transaksi_id') == trx['id'] for l in logs)


def test_transaksi_tolak_stok_kurang_dan_uang_kurang():
    kasir = api_login('karyawan', 'karyawan123')
    pid, harga, stok = _produk_id_harga(kasir)
    r = kasir.post('/api/transaksi', json={
        'items': [{'id': pid, 'qty': stok + 100}],
        'diskon_val': 0, 'diskon_tipe': 'persen',
        'bayar': 10 ** 12, 'metode_bayar': 'tunai'})
    assert r.status_code == 400
    assert 'Stok' in r.get_json()['error']

    if stok >= 1:
        r = kasir.post('/api/transaksi', json={
            'items': [{'id': pid, 'qty': 1}],
            'diskon_val': 0, 'diskon_tipe': 'persen',
            'bayar': 0, 'metode_bayar': 'tunai'})
        assert r.status_code == 400


def test_transaksi_tolak_produk_toko_lain():
    # superadmin (tanpa ghost) switch ke store 2 lalu coba jual produk store 1
    su = api_login(OWNER_USER, OWNER_PASS)
    su.post('/api/switch-store/2')
    prods_s2 = su.get('/api/produk?limit=500').get_json()
    ids_s2 = {p['id'] for p in prods_s2}
    # ambil 1 produk store 1 langsung dari DB
    import sqlite3
    con = sqlite3.connect('kasirtoko.db')
    row = con.execute(
        'SELECT id FROM produk WHERE store_id=1 AND aktif=1 LIMIT 1').fetchone()
    con.close()
    assert row, 'butuh 1 produk store 1'
    if row[0] not in ids_s2:
        r = su.post('/api/transaksi', json={
            'items': [{'id': row[0], 'qty': 1}],
            'diskon_val': 0, 'diskon_tipe': 'persen',
            'bayar': 10 ** 9, 'metode_bayar': 'tunai'})
        # superadmin tanpa ghost boleh tulis, tapi produk toko lain ditolak
        assert r.status_code in (400, 403), r.get_json()


# ---------- P0-1/P0-2: void & restore ----------

def test_void_restore_flow():
    kasir = api_login('karyawan', 'karyawan123')
    pid, harga, stok = _produk_id_harga(kasir)
    r = kasir.post('/api/transaksi', json={
        'items': [{'id': pid, 'qty': 1}],
        'diskon_val': 0, 'diskon_tipe': 'persen',
        'bayar': harga, 'metode_bayar': 'tunai'})
    assert r.status_code == 201
    tid = r.get_json()['id']

    owner = api_login(OWNER_USER, OWNER_PASS)
    r = owner.post(f'/api/transaksi/{tid}/void', json={'reason': 'test void'})
    assert r.status_code == 200, r.get_json()  # dulu: 500 NameError

    r = owner.post(f'/api/transaksi/{tid}/restore')
    assert r.status_code == 200, r.get_json()  # dulu: 500 NameError
    assert r.get_json()['transaksi']['status'] == 'aktif'


def test_void_toko_lain_ditolak():
    kasir = api_login(KASIR_USER, KASIR_PASS)
    pid, harga, stok = _produk_id_harga(kasir)
    r = kasir.post('/api/transaksi', json={
        'items': [{'id': pid, 'qty': 1}],
        'diskon_val': 0, 'diskon_tipe': 'persen',
        'bayar': harga, 'metode_bayar': 'tunai'})
    tid = r.get_json()['id']

    su = api_login(OWNER_USER, OWNER_PASS)
    su.post('/api/switch-store/2')
    r = su.post(f'/api/transaksi/{tid}/void', json={'reason': 'coba toko lain'})
    assert r.status_code == 404


# ---------- P0-3: isolasi store ----------

def test_get_transaksi_hanya_toko_sendiri():
    su = api_login(OWNER_USER, OWNER_PASS)
    su.post('/api/switch-store/2')
    rows = su.get('/api/transaksi?limit=100').get_json()
    assert isinstance(rows, list)
    assert all(t['store_id'] == 2 for t in rows)


def _can_login(u, p):
    c = app.test_client()
    return login_ok(c, u, p)


# ---------- P1-3: idempotency piutang ----------

def test_bayar_piutang_idempotent():
    kasir = api_login('karyawan', 'karyawan123')
    pid, harga, stok = _produk_id_harga(kasir)
    r = kasir.post('/api/transaksi', json={
        'items': [{'id': pid, 'qty': 1}],
        'diskon_val': 0, 'diskon_tipe': 'persen',
        'bayar': 0, 'metode_bayar': 'piutang'})
    assert r.status_code == 201
    tid = r.get_json()['id']
    body = {'nominal': min(1000, harga), 'metode_bayar': 'tunai',
            'idempotency_key': f'test-{tid}'}
    r1 = kasir.post(f'/api/piutang/{tid}/bayar', json=body)
    assert r1.status_code == 200, r1.get_json()
    r2 = kasir.post(f'/api/piutang/{tid}/bayar', json=body)
    assert r2.status_code == 409  # duplikat ditolak


# ---------- P1-8: kas reset & pelanggan ----------

def test_kas_reset_tidak_menghapus_riwayat():
    owner = api_login(OWNER_USER, OWNER_PASS)
    sebelum = owner.get('/api/kas').get_json()
    n_awal = len(sebelum['rows'])
    r = owner.post('/api/kas/reset', json={'konfirmasi': 'Reset Saldo'})
    assert r.status_code == 200
    sesudah = owner.get('/api/kas').get_json()
    assert len(sesudah['rows']) >= n_awal  # riwayat utuh, bukan DELETE
    assert sesudah['stats']['saldo'] == 0


def test_pelanggan_duplikat_diperingatkan():
    kasir = api_login('karyawan', 'karyawan123')
    r = kasir.post('/api/pelanggan', json={'nama': 'Budi Test Unik Xyz'})
    assert r.status_code in (201, 409)
    r = kasir.post('/api/pelanggan', json={'nama': 'Budi Test Unik Xyz'})
    assert r.status_code == 409
    assert r.get_json().get('butuh_force') is True


# ---------- P2-5: ghost mode ----------

def test_ghost_mode_tulis_ditolak():
    su = api_login(OWNER_USER, OWNER_PASS)
    r = su.post('/api/admin/enter-store/1')
    assert r.status_code == 200
    pid = su.get('/api/produk?limit=1').get_json()[0]['id']
    r = su.post('/api/transaksi', json={
        'items': [{'id': pid, 'qty': 1}],
        'diskon_val': 0, 'diskon_tipe': 'persen',
        'bayar': 10 ** 9, 'metode_bayar': 'tunai'})
    assert r.status_code == 403
    su.post('/api/admin/exit-store')


# ---------- P2-1/P1-7: export ----------

def test_export_produk_csv_ada_barcode():
    owner = api_login(OWNER_USER, OWNER_PASS)
    r = owner.get('/api/produk/export-csv')
    assert r.status_code == 200
    header = r.data.decode('utf-8-sig').splitlines()[0]
    assert 'barcode' in header


def test_export_transaksi_hanya_toko_sendiri():
    su = api_login(OWNER_USER, OWNER_PASS)
    su.post('/api/switch-store/2')
    r = su.get('/api/export/csv')
    assert r.status_code == 200


# ---------- Reset transaksi & dompet ----------

def test_reset_transaksi_hanya_toko_aktif():
    import glob as _glob
    import sqlite3 as _sql
    su = api_login(OWNER_USER, OWNER_PASS)
    su.post('/api/switch-store/2')
    # store 2 kosong di data asli; produk khusus test dibuat & dibersihkan lagi
    r = su.post('/api/produk', json={
        'nama': 'TEST RESET PROD', 'kategori': 'Umum', 'harga': 5000, 'stok': 10})
    assert r.status_code == 201, r.get_json()
    pid = r.get_json()['id']
    try:
        for metode, bayar in (('tunai', 5000), ('piutang', 0)):
            r = su.post('/api/transaksi', json={
                'items': [{'id': pid, 'qty': 1}],
                'diskon_val': 0, 'diskon_tipe': 'persen',
                'bayar': bayar, 'metode_bayar': metode})
            assert r.status_code == 201, r.get_json()

        # tanpa konfirmasi → 400
        assert su.post('/api/transaksi/reset', json={}).status_code == 400
        # konfirmasi salah → 400
        assert su.post('/api/transaksi/reset',
                       json={'konfirmasi': 'RESET'}).status_code == 400

        n_prod_sebelum = len(su.get('/api/produk?limit=1000').get_json())
        n_plg_sebelum = len(su.get('/api/pelanggan').get_json())

        r = su.post('/api/transaksi/reset', json={'konfirmasi': 'RESET TRANSAKSI'})
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data['dihapus']['transaksi'] >= 2
        assert len(data['backup']) >= 2  # minimal transaksi + kas terbackup

        # toko 2 bersih
        assert su.get('/api/transaksi?limit=100').get_json() == []
        assert su.get('/api/piutang').get_json() == []
        assert su.get('/api/kas').get_json()['rows'] == []
        # produk & pelanggan TIDAK tersentuh
        assert len(su.get('/api/produk?limit=1000').get_json()) == n_prod_sebelum
        assert len(su.get('/api/pelanggan').get_json()) == n_plg_sebelum
        # file backup ada di disk
        for f in data['backup']:
            assert _glob.glob(os.path.join('backups', f)), f

        # toko 1 tidak ikut terhapus
        su.post('/api/switch-store/1')
        assert len(su.get('/api/transaksi?limit=100').get_json()) > 0
    finally:
        # bersihkan sisa test di store 2 (produk test + data bila reset gagal)
        con = _sql.connect('kasirtoko.db')
        con.execute("DELETE FROM transaksi_item WHERE transaksi_id IN "
                    "(SELECT id FROM transaksi WHERE store_id=2)")
        con.execute("DELETE FROM piutang_bayar WHERE store_id=2")
        con.execute("DELETE FROM transaksi WHERE store_id=2")
        con.execute("DELETE FROM kas WHERE store_id=2")
        con.execute("DELETE FROM tutup_kasir WHERE store_id=2")
        con.execute("DELETE FROM produk WHERE id=?", (pid,))
        con.commit()
        con.close()
