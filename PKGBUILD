# Maintainer: Your Name <you@example.com>

pkgname=mypaint
pkgver=0.1.0
pkgrel=1
pkgdesc="Minimal MS Paint clone for Linux"
arch=('any')
url="https://github.com/your-username/mypaint"
license=('MIT')
depends=(
    'python'
    'python-pyside6'
)
makedepends=(
    'uv'
    'python-installer'
)
source=("$pkgname-$pkgver.tar.gz::https://github.com/your-username/mypaint/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$srcdir/$pkgname-$pkgver"
    uv build --wheel
}

package() {
    cd "$srcdir/$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl

    install -Dm644 mypaint.desktop "$pkgdir/usr/share/applications/mypaint.desktop"
    install -Dm644 mypaint.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/mypaint.svg"
}
