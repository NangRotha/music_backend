from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
try:
    from .database import Base
except (ImportError, ValueError):
    from database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    site_name_en = Column(String(100), default="MelodyKhmer Store")
    site_name_kh = Column(String(100), default="ហាងតន្ត្រី មេឡូឌីខ្មែរ")
    logo_url = Column(String(500), default="")
    telegram_username = Column(String(100), default="admin_music_store") # Telegram username without @
    telegram_channel = Column(String(255), default="https://t.me/music_channel")
    currency_symbol = Column(String(10), default="$")
    contact_phone = Column(String(50), default="+855 12 345 678")
    banner_title_en = Column(String(200), default="Discover & Buy Original Khmer & Global Music")
    banner_title_kh = Column(String(200), default="ស្វែងរក និងទិញបទចម្រៀងពិរោះៗខ្មែរ និងអន្តរជាតិ")
    banner_sub_en = Column(String(300), default="No registration needed. Instant Telegram checkout with exclusive discounts & promo codes.")
    banner_sub_kh = Column(String(300), default="មិនបាច់ចុះឈ្មោះ មិនបាច់ Login។ ទិញផ្ទាល់តាម Telegram ជាមួយការបញ្ចុះតម្លៃពិសេស។")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Music(Base):
    __tablename__ = "music"

    id = Column(Integer, primary_key=True, index=True)
    title_en = Column(String(200), nullable=False, index=True)
    title_kh = Column(String(200), nullable=True)
    artist_en = Column(String(150), nullable=False, index=True)
    artist_kh = Column(String(150), nullable=True)
    genre = Column(String(100), default="Pop", index=True)
    price = Column(Float, nullable=False, default=5.0)
    discount_percent = Column(Float, default=0.0) # e.g. 15.0 for 15% off
    cover_image_url = Column(String(500), default="")
    preview_audio_url = Column(String(500), default="")
    description_en = Column(Text, default="")
    description_kh = Column(Text, default="")
    duration = Column(String(20), default="3:45")
    is_featured = Column(Boolean, default=False)
    play_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_type = Column(String(20), default="percent") # "percent" or "fixed"
    discount_value = Column(Float, nullable=False) # e.g. 20 for 20% or 5 for $5 off
    min_spend = Column(Float, default=0.0)
    max_discount = Column(Float, nullable=True) # Cap on discount amount
    usage_limit = Column(Integer, nullable=True) # Null = unlimited
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class OrderInquiry(Base):
    __tablename__ = "order_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    reference_code = Column(String(50), unique=True, index=True)
    music_id = Column(Integer, ForeignKey("music.id", ondelete="SET NULL"), nullable=True)
    music_title = Column(String(200), nullable=False)
    music_artist = Column(String(150), default="")
    original_price = Column(Float, nullable=False)
    track_discount = Column(Float, default=0.0)
    promo_code = Column(String(50), nullable=True)
    promo_discount = Column(Float, default=0.0)
    final_price = Column(Float, nullable=False)
    customer_name = Column(String(100), default="")
    customer_telegram = Column(String(100), default="")
    customer_phone = Column(String(50), default="")
    status = Column(String(30), default="initiated") # initiated, confirmed, completed, cancelled
    telegram_url = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertPopup(Base):
    __tablename__ = "alert_popups"

    id = Column(Integer, primary_key=True, index=True)
    title_en = Column(String(200), nullable=False)
    title_kh = Column(String(200), nullable=True)
    message_en = Column(Text, nullable=False)
    message_kh = Column(Text, nullable=True)
    date = Column(String(100), nullable=True) # Date of announcement / event
    expire_date = Column(String(100), nullable=True) # Expiry date (e.g. 2026-09-30)
    badge_en = Column(String(80), nullable=True, default="Special Notice")
    badge_kh = Column(String(80), nullable=True, default="ដំណឹងពិសេស")
    image_url = Column(String(500), nullable=True) # Optional announcement flyer/image
    link_url = Column(String(500), nullable=True)
    link_text_en = Column(String(100), nullable=True, default="Learn More")
    link_text_kh = Column(String(100), nullable=True, default="ស្វែងយល់បន្ថែម")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AboutSection(Base):
    __tablename__ = "about_sections"

    id = Column(Integer, primary_key=True, index=True)
    title_en = Column(String(200), nullable=False)
    title_kh = Column(String(200), nullable=True)
    subtitle_en = Column(String(250), nullable=True)
    subtitle_kh = Column(String(250), nullable=True)
    content_en = Column(Text, nullable=False)
    content_kh = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    badge_en = Column(String(80), nullable=True, default="About Us")
    badge_kh = Column(String(80), nullable=True, default="អំពីយើង")
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Slide(Base):
    __tablename__ = "slides"

    id = Column(Integer, primary_key=True, index=True)
    title_en = Column(String(255), nullable=False)
    title_kh = Column(String(255), nullable=True)
    subtitle_en = Column(String(255), nullable=True)
    subtitle_kh = Column(String(255), nullable=True)
    badge_en = Column(String(100), nullable=True, default="Featured")
    badge_kh = Column(String(100), nullable=True, default="ពិសេស")
    media_type = Column(String(50), default="image") # "image", "video", "youtube"
    media_url = Column(String(500), nullable=False) # image URL, mp4 video URL, or YouTube URL
    thumbnail_url = Column(String(500), nullable=True) # video poster or preview image
    link_url = Column(String(500), nullable=True)
    link_text_en = Column(String(100), nullable=True, default="Explore Now")
    link_text_kh = Column(String(100), nullable=True, default="ស្វែងរកឥឡូវនេះ")
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name_en = Column(String(100), nullable=False, unique=True, index=True)
    name_kh = Column(String(150), nullable=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description_en = Column(String(255), nullable=True)
    description_kh = Column(String(255), nullable=True)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
