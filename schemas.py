from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# Admin Schemas
class AdminLogin(BaseModel):
    username: str
    password: str

class AdminChangeCredentials(BaseModel):
    current_password: str
    new_username: Optional[str] = None
    new_password: Optional[str] = None

class AdminOut(BaseModel):
    id: int
    username: str
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminOut

# Settings Schemas
class SettingsBase(BaseModel):
    site_name_en: str
    site_name_kh: str
    logo_url: Optional[str] = ""
    telegram_username: str
    telegram_channel: Optional[str] = ""
    currency_symbol: str = "$"
    contact_phone: Optional[str] = ""
    banner_title_en: Optional[str] = ""
    banner_title_kh: Optional[str] = ""
    banner_sub_en: Optional[str] = ""
    banner_sub_kh: Optional[str] = ""

class SettingsUpdate(BaseModel):
    site_name_en: Optional[str] = None
    site_name_kh: Optional[str] = None
    logo_url: Optional[str] = None
    telegram_username: Optional[str] = None
    telegram_channel: Optional[str] = None
    currency_symbol: Optional[str] = None
    contact_phone: Optional[str] = None
    banner_title_en: Optional[str] = None
    banner_title_kh: Optional[str] = None
    banner_sub_en: Optional[str] = None
    banner_sub_kh: Optional[str] = None

class SettingsOut(SettingsBase):
    id: int
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Music Schemas
class MusicBase(BaseModel):
    title_en: str
    title_kh: Optional[str] = ""
    artist_en: str
    artist_kh: Optional[str] = ""
    genre: str = "Pop"
    price: float = Field(..., ge=0)
    discount_percent: float = Field(0.0, ge=0, le=100)
    cover_image_url: Optional[str] = ""
    preview_audio_url: Optional[str] = ""
    description_en: Optional[str] = ""
    description_kh: Optional[str] = ""
    duration: Optional[str] = "3:45"
    is_featured: bool = False

class MusicCreate(MusicBase):
    pass

class MusicUpdate(BaseModel):
    title_en: Optional[str] = None
    title_kh: Optional[str] = None
    artist_en: Optional[str] = None
    artist_kh: Optional[str] = None
    genre: Optional[str] = None
    price: Optional[float] = None
    discount_percent: Optional[float] = None
    cover_image_url: Optional[str] = None
    preview_audio_url: Optional[str] = None
    description_en: Optional[str] = None
    description_kh: Optional[str] = None
    duration: Optional[str] = None
    is_featured: Optional[bool] = None

class MusicOut(MusicBase):
    id: int
    play_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    sale_price: float = 0.0

    class Config:
        from_attributes = True

# PromoCode Schemas
class PromoCodeBase(BaseModel):
    code: str
    discount_type: str = "percent" # percent, fixed
    discount_value: float = Field(..., gt=0)
    min_spend: float = 0.0
    max_discount: Optional[float] = None
    usage_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True

class PromoCodeCreate(PromoCodeBase):
    pass

class PromoCodeUpdate(BaseModel):
    code: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    min_spend: Optional[float] = None
    max_discount: Optional[float] = None
    usage_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None

class PromoCodeOut(PromoCodeBase):
    id: int
    used_count: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# Promo Validation
class PromoValidateRequest(BaseModel):
    code: str
    music_id: Optional[int] = None
    amount: float = Field(..., ge=0)

class PromoValidateResponse(BaseModel):
    valid: bool
    code: str
    discount_type: str
    discount_value: float
    discount_amount: float
    final_amount: float
    message_en: str
    message_kh: str

# Order / Telegram Inquiry
class OrderInquiryCreate(BaseModel):
    music_id: int
    promo_code: Optional[str] = None
    customer_name: Optional[str] = ""
    customer_telegram: Optional[str] = ""
    customer_phone: Optional[str] = ""

class OrderInquiryOut(BaseModel):
    id: int
    reference_code: str
    music_id: Optional[int]
    music_title: str
    music_artist: str
    original_price: float
    track_discount: float
    promo_code: Optional[str]
    promo_discount: float
    final_price: float
    customer_name: Optional[str]
    customer_telegram: Optional[str]
    status: str
    telegram_url: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# Alert Popup Schemas
class AlertPopupBase(BaseModel):
    title_en: str
    title_kh: Optional[str] = None
    message_en: str
    message_kh: Optional[str] = None
    date: Optional[str] = None
    expire_date: Optional[str] = None
    image_url: Optional[str] = None
    badge_en: Optional[str] = "Special Notice"
    badge_kh: Optional[str] = "ដំណឹងពិសេស"
    link_url: Optional[str] = None
    link_text_en: Optional[str] = "Learn More"
    link_text_kh: Optional[str] = "ស្វែងយល់បន្ថែម"
    is_active: bool = True

class AlertPopupCreate(AlertPopupBase):
    pass

class AlertPopupUpdate(BaseModel):
    title_en: Optional[str] = None
    title_kh: Optional[str] = None
    message_en: Optional[str] = None
    message_kh: Optional[str] = None
    date: Optional[str] = None
    expire_date: Optional[str] = None
    image_url: Optional[str] = None
    badge_en: Optional[str] = None
    badge_kh: Optional[str] = None
    link_url: Optional[str] = None
    link_text_en: Optional[str] = None
    link_text_kh: Optional[str] = None
    is_active: Optional[bool] = None

class AlertPopupOut(AlertPopupBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# About Us Schemas
class AboutSectionBase(BaseModel):
    title_en: str
    title_kh: Optional[str] = None
    subtitle_en: Optional[str] = None
    subtitle_kh: Optional[str] = None
    content_en: str
    content_kh: Optional[str] = None
    image_url: Optional[str] = None
    badge_en: Optional[str] = "About Us"
    badge_kh: Optional[str] = "អំពីយើង"
    order_index: int = 0
    is_active: bool = True

class AboutSectionCreate(AboutSectionBase):
    pass

class AboutSectionUpdate(BaseModel):
    title_en: Optional[str] = None
    title_kh: Optional[str] = None
    subtitle_en: Optional[str] = None
    subtitle_kh: Optional[str] = None
    content_en: Optional[str] = None
    content_kh: Optional[str] = None
    image_url: Optional[str] = None
    badge_en: Optional[str] = None
    badge_kh: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None

class AboutSectionOut(AboutSectionBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Slide / Banner Carousel Schemas
class SlideBase(BaseModel):
    title_en: str
    title_kh: Optional[str] = None
    subtitle_en: Optional[str] = None
    subtitle_kh: Optional[str] = None
    badge_en: Optional[str] = "Featured"
    badge_kh: Optional[str] = "ពិសេស"
    media_type: str = "image"  # "image", "video", "youtube"
    media_url: str
    thumbnail_url: Optional[str] = None
    link_url: Optional[str] = None
    link_text_en: Optional[str] = "Explore Now"
    link_text_kh: Optional[str] = "ស្វែងរកឥឡូវនេះ"
    order_index: int = 0
    is_active: bool = True

class SlideCreate(SlideBase):
    pass

class SlideUpdate(BaseModel):
    title_en: Optional[str] = None
    title_kh: Optional[str] = None
    subtitle_en: Optional[str] = None
    subtitle_kh: Optional[str] = None
    badge_en: Optional[str] = None
    badge_kh: Optional[str] = None
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    link_url: Optional[str] = None
    link_text_en: Optional[str] = None
    link_text_kh: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None

class SlideOut(SlideBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Category / Genre Schemas
class CategoryBase(BaseModel):
    name_en: str = Field(..., max_length=100)
    name_kh: Optional[str] = Field(None, max_length=150)
    slug: Optional[str] = Field(None, max_length=100)
    description_en: Optional[str] = Field(None, max_length=255)
    description_kh: Optional[str] = Field(None, max_length=255)
    order_index: int = 0
    is_active: bool = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name_en: Optional[str] = None
    name_kh: Optional[str] = None
    slug: Optional[str] = None
    description_en: Optional[str] = None
    description_kh: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None

class CategoryOut(CategoryBase):
    id: int
    track_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
