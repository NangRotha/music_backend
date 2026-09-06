import os
import sys
import urllib.parse
import uuid
from datetime import datetime
from typing import Optional, List
import shutil

# Ensure the backend directory and workspace are accessible in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

try:
    from .database import engine, Base, get_db
    from .models import Admin, Settings, Music, PromoCode, OrderInquiry, AlertPopup, AboutSection, Slide, Category
    from .schemas import (
        AdminLogin, AdminChangeCredentials, AdminOut, TokenResponse,
        SettingsOut, SettingsUpdate,
        MusicOut, MusicCreate, MusicUpdate,
        PromoCodeOut, PromoCodeCreate, PromoCodeUpdate,
        PromoValidateRequest, PromoValidateResponse,
        OrderInquiryCreate, OrderInquiryOut,
        AlertPopupOut, AlertPopupCreate, AlertPopupUpdate,
        AboutSectionOut, AboutSectionCreate, AboutSectionUpdate,
        SlideOut, SlideCreate, SlideUpdate,
        CategoryOut, CategoryCreate, CategoryUpdate
    )
    from .auth import hash_password, verify_password, create_access_token, get_current_admin
    from .seed import seed_database, UPLOAD_DIR
    from .uploadthing_client import upload_file_to_uploadthing
except (ImportError, ValueError):
    from database import engine, Base, get_db
    from models import Admin, Settings, Music, PromoCode, OrderInquiry, AlertPopup, AboutSection, Slide, Category
    from schemas import (
        AdminLogin, AdminChangeCredentials, AdminOut, TokenResponse,
        SettingsOut, SettingsUpdate,
        MusicOut, MusicCreate, MusicUpdate,
        PromoCodeOut, PromoCodeCreate, PromoCodeUpdate,
        PromoValidateRequest, PromoValidateResponse,
        OrderInquiryCreate, OrderInquiryOut,
        AlertPopupOut, AlertPopupCreate, AlertPopupUpdate,
        AboutSectionOut, AboutSectionCreate, AboutSectionUpdate,
        SlideOut, SlideCreate, SlideUpdate,
        CategoryOut, CategoryCreate, CategoryUpdate
    )
    from auth import hash_password, verify_password, create_access_token, get_current_admin
    from seed import seed_database, UPLOAD_DIR
    from uploadthing_client import upload_file_to_uploadthing

app = FastAPI(
    title="KhmerBeats Music Store API",
    description="Backend API for Music E-Commerce with Telegram Checkout, Promo Codes, and Admin CMS",
    version="1.0.0"
)

# Enable CORS for user & admin frontends (configurable via CORS_ORIGINS)
cors_origins_env = os.getenv("CORS_ORIGINS", "*").strip()
if not cors_origins_env or cors_origins_env == "*":
    origins = ["*"]
    origin_regex = r"^https?:\/\/.*"
else:
    origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
    origin_regex = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origin_regex is None else [],
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.on_event("startup")
def on_startup():
    seed_database()

# Helper to calculate music sale price
def attach_sale_price(m: Music) -> dict:
    discount = (m.discount_percent or 0.0) / 100.0
    sale_price = max(0.0, round(m.price * (1.0 - discount), 2))
    data = {
        "id": m.id,
        "title_en": m.title_en,
        "title_kh": m.title_kh or m.title_en,
        "artist_en": m.artist_en,
        "artist_kh": m.artist_kh or m.artist_en,
        "genre": m.genre,
        "price": m.price,
        "discount_percent": m.discount_percent,
        "sale_price": sale_price,
        "cover_image_url": m.cover_image_url,
        "preview_audio_url": m.preview_audio_url,
        "description_en": m.description_en,
        "description_kh": m.description_kh,
        "duration": m.duration,
        "is_featured": m.is_featured,
        "play_count": m.play_count,
        "created_at": m.created_at,
        "updated_at": m.updated_at
    }
    return data

# ==================== SETTINGS ROUTES ====================
@app.get("/api/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings

@app.put("/api/settings", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)
    
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            # Clean telegram username if user typed with @
            if key == "telegram_username" and isinstance(value, str):
                value = value.strip().lstrip("@")
            setattr(settings, key, value)
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    return settings

# ==================== ADMIN AUTH ROUTES ====================
@app.post("/api/admin/login", response_model=TokenResponse)
def admin_login(payload: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == payload.username.strip()).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password / ឈ្មោះ ឬលេខសម្ងាត់មិនត្រឹមត្រូវ"
        )
    
    token = create_access_token(data={"sub": admin.username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "admin": admin
    }

@app.get("/api/admin/me", response_model=AdminOut)
def get_admin_profile(admin: Admin = Depends(get_current_admin)):
    return admin

@app.put("/api/admin/change-credentials")
def change_admin_credentials(
    payload: AdminChangeCredentials,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    if not verify_password(payload.current_password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password incorrect / លេខសម្ងាត់បច្ចុប្បន្នមិនត្រឹមត្រូវទេ"
        )
    
    if payload.new_username and payload.new_username.strip():
        new_u = payload.new_username.strip()
        existing = db.query(Admin).filter(Admin.username == new_u, Admin.id != admin.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already in use / ឈ្មោះនេះមានរួចហើយ")
        admin.username = new_u
    
    if payload.new_password and len(payload.new_password) >= 6:
        admin.password_hash = hash_password(payload.new_password)
    elif payload.new_password:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    admin.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(admin)
    return {"message": "Credentials updated successfully / បានផ្លាស់ប្ដូរដោយជោគជ័យ", "username": admin.username}

# ==================== MUSIC CATALOG ROUTES ====================
@app.get("/api/music")
def list_music(
    search: Optional[str] = None,
    genre: Optional[str] = None,
    featured: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Music)
    
    if featured is not None:
        query = query.filter(Music.is_featured == featured)
    
    if genre and genre.lower() != "all":
        query = query.filter(Music.genre.ilike(f"%{genre}%"))
        
    if search:
        s = f"%{search}%"
        query = query.filter(
            (Music.title_en.ilike(s)) |
            (Music.title_kh.ilike(s)) |
            (Music.artist_en.ilike(s)) |
            (Music.artist_kh.ilike(s)) |
            (Music.genre.ilike(s))
        )
        
    items = query.order_by(Music.is_featured.desc(), Music.created_at.desc()).all()
    return [attach_sale_price(m) for m in items]

@app.get("/api/music/{id}")
def get_music_detail(id: int, db: Session = Depends(get_db)):
    music = db.query(Music).filter(Music.id == id).first()
    if not music:
        raise HTTPException(status_code=404, detail="Music track not found")
    
    # Increment play count
    music.play_count = (music.play_count or 0) + 1
    db.commit()
    return attach_sale_price(music)

# Helper to attach track count to CategoryOut
def attach_category_count(cat: Category, db: Session) -> dict:
    count = db.query(Music).filter(
        (Music.genre == cat.name_en) | (Music.genre == cat.slug) | (Music.genre == cat.name_kh)
    ).count()
    return {
        "id": cat.id,
        "name_en": cat.name_en,
        "name_kh": cat.name_kh,
        "slug": cat.slug,
        "description_en": cat.description_en,
        "description_kh": cat.description_kh,
        "order_index": cat.order_index,
        "is_active": cat.is_active,
        "track_count": count,
        "created_at": cat.created_at,
        "updated_at": cat.updated_at
    }

# ==================== CATEGORIES / GENRES ROUTES ====================
@app.get("/api/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    """Public list of active categories for storefront and music selectors."""
    cats = db.query(Category).filter(Category.is_active == True).order_by(Category.order_index.asc(), Category.name_en.asc()).all()
    return [attach_category_count(c, db) for c in cats]

@app.get("/api/admin/categories", response_model=List[CategoryOut])
def list_admin_categories(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    """Admin list of all categories including inactive ones with track counts."""
    cats = db.query(Category).order_by(Category.order_index.asc(), Category.name_en.asc()).all()
    return [attach_category_count(c, db) for c in cats]

@app.post("/api/categories", response_model=CategoryOut)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    name_en_clean = payload.name_en.strip()
    slug_clean = payload.slug.strip() if payload.slug else urllib.parse.quote(name_en_clean.lower().replace(" ", "-").replace("/", "-"))
    
    existing = db.query(Category).filter((Category.name_en == name_en_clean) | (Category.slug == slug_clean)).first()
    if existing:
        raise HTTPException(status_code=400, detail="A category with this name or slug already exists")
        
    cat = Category(
        name_en=name_en_clean,
        name_kh=payload.name_kh.strip() if payload.name_kh else None,
        slug=slug_clean,
        description_en=payload.description_en,
        description_kh=payload.description_kh,
        order_index=payload.order_index,
        is_active=payload.is_active
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return attach_category_count(cat, db)

@app.put("/api/categories/{id}", response_model=CategoryOut)
def update_category(id: int, payload: CategoryUpdate, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    cat = db.query(Category).filter(Category.id == id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
        
    update_data = payload.dict(exclude_unset=True)
    if "name_en" in update_data and update_data["name_en"]:
        name_en_clean = update_data["name_en"].strip()
        existing = db.query(Category).filter(Category.name_en == name_en_clean, Category.id != id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Another category already has this name")
        cat.name_en = name_en_clean
        
    if "slug" in update_data and update_data["slug"]:
        slug_clean = update_data["slug"].strip()
        existing = db.query(Category).filter(Category.slug == slug_clean, Category.id != id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Another category already has this slug")
        cat.slug = slug_clean

    for k, v in update_data.items():
        if k not in ["name_en", "slug"]:
            setattr(cat, k, v)

    cat.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cat)
    return attach_category_count(cat, db)

@app.delete("/api/categories/{id}")
def delete_category(id: int, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    cat = db.query(Category).filter(Category.id == id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(cat)
    db.commit()
    return {"message": "Category deleted successfully"}

@app.get("/api/genres")
def list_genres(db: Session = Depends(get_db)):
    active_cats = db.query(Category.name_en).filter(Category.is_active == True).order_by(Category.order_index.asc()).all()
    cat_names = [c[0] for c in active_cats if c[0]]
    
    music_genres = db.query(Music.genre).distinct().all()
    music_genre_names = [g[0] for g in music_genres if g[0] and g[0] not in cat_names]
    
    all_genres = ["All"] + cat_names + music_genre_names
    return all_genres

@app.post("/api/music")
def create_music(
    payload: MusicCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    music = Music(**payload.dict())
    db.add(music)
    db.commit()
    db.refresh(music)
    return attach_sale_price(music)

@app.put("/api/music/{id}")
def update_music(
    id: int,
    payload: MusicUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    music = db.query(Music).filter(Music.id == id).first()
    if not music:
        raise HTTPException(status_code=404, detail="Music track not found")
    
    for key, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            setattr(music, key, value)
            
    music.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(music)
    return attach_sale_price(music)

@app.delete("/api/music/{id}")
def delete_music(
    id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    music = db.query(Music).filter(Music.id == id).first()
    if not music:
        raise HTTPException(status_code=404, detail="Music track not found")
    
    # Detach orders referencing this music
    db.query(OrderInquiry).filter(OrderInquiry.music_id == id).update({"music_id": None})
    db.delete(music)
    db.commit()
    return {"message": "Track deleted successfully"}

# ==================== PROMO CODES ROUTES ====================
@app.post("/api/promos/validate", response_model=PromoValidateResponse)
def validate_promo_code(payload: PromoValidateRequest, db: Session = Depends(get_db)):
    code_str = payload.code.strip().upper()
    promo = db.query(PromoCode).filter(PromoCode.code == code_str).first()
    
    if not promo or not promo.is_active:
        return PromoValidateResponse(
            valid=False,
            code=code_str,
            discount_type="none",
            discount_value=0.0,
            discount_amount=0.0,
            final_amount=payload.amount,
            message_en="Invalid or inactive promo code",
            message_kh="កូដបញ្ចុះតម្លៃមិនត្រឹមត្រូវ ឬត្រូវបានបិទ"
        )
        
    if promo.expires_at and promo.expires_at < datetime.utcnow():
        return PromoValidateResponse(
            valid=False,
            code=code_str,
            discount_type=promo.discount_type,
            discount_value=promo.discount_value,
            discount_amount=0.0,
            final_amount=payload.amount,
            message_en="Promo code has expired",
            message_kh="កូដបញ្ចុះតម្លៃនេះផុតកំណត់ហើយ"
        )
        
    if promo.usage_limit and promo.used_count >= promo.usage_limit:
        return PromoValidateResponse(
            valid=False,
            code=code_str,
            discount_type=promo.discount_type,
            discount_value=promo.discount_value,
            discount_amount=0.0,
            final_amount=payload.amount,
            message_en="Promo code usage limit reached",
            message_kh="កូដបញ្ចុះតម្លៃនេះបានប្រើអស់ចំនួនកំណត់ហើយ"
        )
        
    if payload.amount < promo.min_spend:
        return PromoValidateResponse(
            valid=False,
            code=code_str,
            discount_type=promo.discount_type,
            discount_value=promo.discount_value,
            discount_amount=0.0,
            final_amount=payload.amount,
            message_en=f"Minimum spend of ${promo.min_spend:.2f} required",
            message_kh=f"ទាមទារការទិញចាប់ពី ${promo.min_spend:.2f} ឡើងទៅ"
        )
        
    # Calculate discount
    if promo.discount_type == "percent":
        discount = payload.amount * (promo.discount_value / 100.0)
        if promo.max_discount and discount > promo.max_discount:
            discount = promo.max_discount
    else: # fixed
        discount = min(payload.amount, promo.discount_value)
        
    discount = round(discount, 2)
    final_amount = max(0.0, round(payload.amount - discount, 2))
    
    return PromoValidateResponse(
        valid=True,
        code=code_str,
        discount_type=promo.discount_type,
        discount_value=promo.discount_value,
        discount_amount=discount,
        final_amount=final_amount,
        message_en=f"Promo applied! Saved ${discount:.2f}",
        message_kh=f"បានអនុវត្តកូដ! ចំណេញបាន ${discount:.2f}"
    )

@app.get("/api/promos/public", response_model=List[PromoCodeOut])
def list_public_promos(db: Session = Depends(get_db)):
    """Public endpoint for storefront to fetch active, valid hot promo codes."""
    now = datetime.utcnow()
    promos = db.query(PromoCode).filter(PromoCode.is_active == True).order_by(PromoCode.created_at.desc()).all()
    valid_promos = []
    for p in promos:
        if p.expires_at and p.expires_at < now:
            continue
        if p.usage_limit and p.used_count >= p.usage_limit:
            continue
        valid_promos.append(p)
    return valid_promos

@app.get("/api/promos", response_model=List[PromoCodeOut])
def list_promos(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    return db.query(PromoCode).order_by(PromoCode.created_at.desc()).all()

@app.post("/api/promos", response_model=PromoCodeOut)
def create_promo(
    payload: PromoCodeCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    code_str = payload.code.strip().upper()
    existing = db.query(PromoCode).filter(PromoCode.code == code_str).first()
    if existing:
        raise HTTPException(status_code=400, detail="Promo code already exists")
        
    promo = PromoCode(**payload.dict())
    promo.code = code_str
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return promo

@app.put("/api/promos/{id}", response_model=PromoCodeOut)
def update_promo(
    id: int,
    payload: PromoCodeUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    promo = db.query(PromoCode).filter(PromoCode.id == id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
        
    for key, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            if key == "code":
                value = value.strip().upper()
            setattr(promo, key, value)
            
    db.commit()
    db.refresh(promo)
    return promo

@app.delete("/api/promos/{id}")
def delete_promo(
    id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    promo = db.query(PromoCode).filter(PromoCode.id == id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
        
    db.delete(promo)
    db.commit()
    return {"message": "Promo code deleted successfully"}

# ==================== TELEGRAM CHECKOUT & ORDERS ====================
@app.post("/api/orders/inquiry", response_model=OrderInquiryOut)
def create_order_inquiry(payload: OrderInquiryCreate, db: Session = Depends(get_db)):
    music = db.query(Music).filter(Music.id == payload.music_id).first()
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")
        
    settings = db.query(Settings).first()
    telegram_username = settings.telegram_username if settings and settings.telegram_username else "admin_music_store"
    currency = settings.currency_symbol if settings and settings.currency_symbol else "$"
    
    # Calculate track price and discount
    original_price = music.price
    track_discount_pct = music.discount_percent or 0.0
    track_discount_amt = round(original_price * (track_discount_pct / 100.0), 2)
    after_track_price = round(original_price - track_discount_amt, 2)
    
    # Check promo code if any
    promo_code_used = None
    promo_discount_amt = 0.0
    if payload.promo_code and payload.promo_code.strip():
        code_str = payload.promo_code.strip().upper()
        promo = db.query(PromoCode).filter(PromoCode.code == code_str, PromoCode.is_active == True).first()
        if promo:
            if not promo.expires_at or promo.expires_at >= datetime.utcnow():
                if not promo.usage_limit or promo.used_count < promo.usage_limit:
                    if after_track_price >= promo.min_spend:
                        promo_code_used = code_str
                        if promo.discount_type == "percent":
                            promo_discount_amt = after_track_price * (promo.discount_value / 100.0)
                            if promo.max_discount and promo_discount_amt > promo.max_discount:
                                promo_discount_amt = promo.max_discount
                        else:
                            promo_discount_amt = min(after_track_price, promo.discount_value)
                        promo_discount_amt = round(promo_discount_amt, 2)
                        # Increment promo usage
                        promo.used_count += 1
                        
    final_price = max(0.0, round(after_track_price - promo_discount_amt, 2))
    ref_code = f"MK-{uuid.uuid4().hex[:6].upper()}"
    
    # Generate Telegram message
    title_display = f"{music.title_en}" + (f" ({music.title_kh})" if music.title_kh else "")
    artist_display = f"{music.artist_en}" + (f" ({music.artist_kh})" if music.artist_kh else "")
    
    lines = [
        "[ORDER RECEIPT / វិក្កយបត្របញ្ជាទិញ]",
        "──────────────────────────────",
        f"Order Ref: #{ref_code}",
        f"Song: {title_display}",
        f"Artist: {artist_display}",
        f"Base Price: {currency}{original_price:.2f}",
    ]
    if track_discount_amt > 0:
        lines.append(f"Track Discount: -{currency}{track_discount_amt:.2f} ({track_discount_pct:.0f}%)")
    if promo_code_used:
        lines.append(f"Promo Code: {promo_code_used} (-{currency}{promo_discount_amt:.2f})")
    
    lines.extend([
        f"Final Total: {currency}{final_price:.2f}",
        "──────────────────────────────",
        "Hello Admin, I want to purchase this music.",
        "(សូមជម្រាបសួរ Admin ខ្ញុំចង់ទិញបទចម្រៀងនេះបាទ/ចាស)"
    ])
    
    telegram_msg = "\n".join(lines)
    encoded_msg = urllib.parse.quote(telegram_msg)
    telegram_url = f"https://t.me/{telegram_username}?text={encoded_msg}"
    
    order = OrderInquiry(
        reference_code=ref_code,
        music_id=music.id,
        music_title=music.title_en,
        music_artist=music.artist_en,
        original_price=original_price,
        track_discount=track_discount_amt,
        promo_code=promo_code_used,
        promo_discount=promo_discount_amt,
        final_price=final_price,
        customer_name=payload.customer_name or "",
        customer_telegram=payload.customer_telegram or "",
        customer_phone=payload.customer_phone or "",
        status="initiated",
        telegram_url=telegram_url
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return order

@app.get("/api/orders", response_model=List[OrderInquiryOut])
def list_orders(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    return db.query(OrderInquiry).order_by(OrderInquiry.created_at.desc()).all()

@app.delete("/api/orders/{id}")
def delete_order(
    id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    order = db.query(OrderInquiry).filter(OrderInquiry.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"message": "Order deleted successfully"}

# ==================== FILE UPLOADS (UPLOADTHING CDN) ====================
@app.get("/api/uploadthing/status")
def get_uploadthing_status():
    token = os.getenv("UPLOADTHING_TOKEN")
    return {
        "status": "connected",
        "provider": "UploadThing v7",
        "app_id": "vudv42k77n",
        "cdn_domain": "https://vudv42k77n.ufs.sh",
        "configured": bool(token)
    }

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    admin: Admin = Depends(get_current_admin)
):
    extension = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex[:12]}{extension}"
    dest_path = os.path.join(UPLOAD_DIR, unique_name)
    
    # Save local copy as backup
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Upload to UploadThing cloud CDN
    content_type = file.content_type or ("image/png" if extension in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"] else "application/octet-stream")
    ut_result = upload_file_to_uploadthing(dest_path, file.filename or unique_name, content_type)
    
    if ut_result and ut_result.get("url"):
        return {
            "url": ut_result["url"],
            "ufsUrl": ut_result.get("ufsUrl", ut_result["url"]),
            "appUrl": ut_result.get("appUrl"),
            "key": ut_result.get("key"),
            "filename": unique_name,
            "original_name": file.filename,
            "provider": "uploadthing"
        }
        
    # Local fallback if offline
    return {
        "url": f"/uploads/{unique_name}",
        "filename": unique_name,
        "original_name": file.filename,
        "provider": "local"
    }

# ==================== ALERT POPUP (CRUD) ====================
@app.get("/api/alerts", response_model=List[AlertPopupOut])
def get_active_alerts(db: Session = Depends(get_db)):
    """Public endpoint: returns currently active and unexpired alert popups for the user music store."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    all_active = db.query(AlertPopup).filter(AlertPopup.is_active == True).order_by(AlertPopup.created_at.desc()).all()
    unexpired = []
    for a in all_active:
        if a.expire_date and a.expire_date.strip():
            # If current date is strictly past the expire_date, consider it expired
            if a.expire_date.strip() < today_str:
                continue
        unexpired.append(a)
    return unexpired

@app.get("/api/admin/alerts", response_model=List[AlertPopupOut])
def get_all_alerts_admin(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: returns all alert popups."""
    return db.query(AlertPopup).order_by(AlertPopup.created_at.desc()).all()

@app.post("/api/admin/alerts", response_model=AlertPopupOut)
def create_alert(
    alert_in: AlertPopupCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: creates a new alert popup with date, expire_date, title, message, link."""
    new_alert = AlertPopup(
        title_en=alert_in.title_en,
        title_kh=alert_in.title_kh or alert_in.title_en,
        message_en=alert_in.message_en,
        message_kh=alert_in.message_kh or alert_in.message_en,
        date=alert_in.date or datetime.utcnow().strftime("%Y-%m-%d"),
        expire_date=alert_in.expire_date,
        image_url=alert_in.image_url,
        badge_en=alert_in.badge_en or "Special Notice",
        badge_kh=alert_in.badge_kh or "ដំណឹងពិសេស",
        link_url=alert_in.link_url,
        link_text_en=alert_in.link_text_en or "Learn More",
        link_text_kh=alert_in.link_text_kh or "ស្វែងយល់បន្ថែម",
        is_active=alert_in.is_active
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    return new_alert

@app.put("/api/admin/alerts/{alert_id}", response_model=AlertPopupOut)
def update_alert(
    alert_id: int,
    alert_in: AlertPopupUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: updates an existing alert popup."""
    alert = db.query(AlertPopup).filter(AlertPopup.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert popup not found")
    
    update_data = alert_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert

@app.delete("/api/admin/alerts/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: deletes an alert popup."""
    alert = db.query(AlertPopup).filter(AlertPopup.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert popup not found")
    
    db.delete(alert)
    db.commit()
    return {"message": "Alert popup deleted successfully", "id": alert_id}

@app.patch("/api/admin/alerts/{alert_id}/toggle", response_model=AlertPopupOut)
def toggle_alert_status(
    alert_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: toggles active status of an alert popup."""
    alert = db.query(AlertPopup).filter(AlertPopup.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert popup not found")
    
    alert.is_active = not alert.is_active
    db.commit()
    db.refresh(alert)
    return alert

# ==================== ABOUT US (CRUD) ====================
@app.get("/api/about", response_model=List[AboutSectionOut])
def get_public_about_sections(db: Session = Depends(get_db)):
    """Public endpoint: returns all active about sections ordered by order_index."""
    return db.query(AboutSection).filter(AboutSection.is_active == True).order_by(AboutSection.order_index.asc(), AboutSection.created_at.asc()).all()

@app.get("/api/admin/about", response_model=List[AboutSectionOut])
def get_admin_about_sections(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: returns all about sections."""
    return db.query(AboutSection).order_by(AboutSection.order_index.asc(), AboutSection.created_at.asc()).all()

@app.post("/api/admin/about", response_model=AboutSectionOut)
def create_about_section(
    about_in: AboutSectionCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: creates a new about section."""
    new_about = AboutSection(
        title_en=about_in.title_en,
        title_kh=about_in.title_kh or about_in.title_en,
        subtitle_en=about_in.subtitle_en,
        subtitle_kh=about_in.subtitle_kh or about_in.subtitle_en,
        content_en=about_in.content_en,
        content_kh=about_in.content_kh or about_in.content_en,
        image_url=about_in.image_url,
        badge_en=about_in.badge_en or "About Us",
        badge_kh=about_in.badge_kh or "អំពីយើង",
        order_index=about_in.order_index,
        is_active=about_in.is_active
    )
    db.add(new_about)
    db.commit()
    db.refresh(new_about)
    return new_about

@app.put("/api/admin/about/{about_id}", response_model=AboutSectionOut)
def update_about_section(
    about_id: int,
    about_in: AboutSectionUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: updates an existing about section."""
    section = db.query(AboutSection).filter(AboutSection.id == about_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="About section not found")
    
    update_data = about_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(section, field, value)
    
    section.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(section)
    return section

@app.delete("/api/admin/about/{about_id}")
def delete_about_section(
    about_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: deletes an about section."""
    section = db.query(AboutSection).filter(AboutSection.id == about_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="About section not found")
    
    db.delete(section)
    db.commit()
    return {"message": "About section deleted successfully", "id": about_id}

@app.patch("/api/admin/about/{about_id}/toggle", response_model=AboutSectionOut)
def toggle_about_status(
    about_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: toggles active status of an about section."""
    section = db.query(AboutSection).filter(AboutSection.id == about_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="About section not found")
    
    section.is_active = not section.is_active
    db.commit()
    db.refresh(section)
    return section

# ==================== BANNER SLIDES (IMAGE, VIDEO, YOUTUBE) ====================
@app.get("/api/slides", response_model=List[SlideOut])
def get_public_slides(db: Session = Depends(get_db)):
    """Public endpoint: returns active banner slides ordered by order_index."""
    return db.query(Slide).filter(Slide.is_active == True).order_by(Slide.order_index.asc(), Slide.id.asc()).all()

@app.get("/api/admin/slides", response_model=List[SlideOut])
def get_admin_slides(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: returns all banner slides."""
    return db.query(Slide).order_by(Slide.order_index.asc(), Slide.id.desc()).all()

@app.post("/api/admin/slides", response_model=SlideOut, status_code=status.HTTP_201_CREATED)
def create_slide(
    slide_data: SlideCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: creates a new banner slide."""
    new_slide = Slide(**slide_data.dict())
    db.add(new_slide)
    db.commit()
    db.refresh(new_slide)
    return new_slide

@app.put("/api/admin/slides/{slide_id}", response_model=SlideOut)
def update_slide(
    slide_id: int,
    slide_data: SlideUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: updates an existing banner slide."""
    slide = db.query(Slide).filter(Slide.id == slide_id).first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    
    update_dict = slide_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(slide, key, value)
    
    slide.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(slide)
    return slide

@app.delete("/api/admin/slides/{slide_id}")
def delete_slide(
    slide_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: deletes a banner slide."""
    slide = db.query(Slide).filter(Slide.id == slide_id).first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    
    db.delete(slide)
    db.commit()
    return {"message": "Slide deleted successfully", "id": slide_id}

@app.patch("/api/admin/slides/{slide_id}/toggle", response_model=SlideOut)
def toggle_slide_status(
    slide_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    """Admin endpoint: toggles active status of a banner slide."""
    slide = db.query(Slide).filter(Slide.id == slide_id).first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    
    slide.is_active = not slide.is_active
    db.commit()
    db.refresh(slide)
    return slide

# ==================== HEALTH & STATS ====================
@app.get("/", tags=["Health"])
def root():
    """Root healthcheck probe for Render."""
    return {
        "status": "online",
        "service": "KhmerBeats Music Store API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", tags=["Health"])
def health():
    """Standard healthcheck probe for Render."""
    return {
        "status": "healthy",
        "service": "KhmerBeats Music Store API",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health", tags=["Health"])
def api_health():
    return {
        "status": "healthy",
        "service": "KhmerBeats Music Store API",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/stats")
def get_stats(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin)
):
    total_music = db.query(Music).count()
    total_promos = db.query(PromoCode).filter(PromoCode.is_active == True).count()
    total_orders = db.query(OrderInquiry).count()
    return {
        "total_music": total_music,
        "total_promos": total_promos,
        "total_orders": total_orders
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    # Automatically resolve module whether executed from repo root or backend dir
    app_module = "backend.main:app" if os.path.isdir("backend") else "main:app"
    print(f"🚀 Starting KhmerBeats API on 0.0.0.0:{port} ({app_module})...")
    uvicorn.run(app_module, host="0.0.0.0", port=port, reload=False)
