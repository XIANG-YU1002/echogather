import { useEffect, useRef, useState } from "react";
import Button from "./Button.jsx";
import { RefreshIcon, UploadIcon } from "./icons.jsx";

/**
 * 圖片裁切（依 Business Rules §13.3，使用者 2026-07-30 決定本批加上）。
 *
 * 刻意不引入裁切套件（使用者裁決）：用原生拖曳事件配合 canvas 輸出，
 * 前端依賴維持只有 react / react-dom / react-router-dom 三個。
 *
 * 運作方式：**整張圖完整顯示、不縮放也不留白**，容器尺寸等於圖片顯示尺寸；
 * 圖上疊一個裁切框，拖曳框body 移動、拖曳四角改變大小。
 *
 * aspectRatio 傳 null 即為自由比例（商品圖用；使用者 2026-07-30 要求不限制比例），
 * 傳數字則鎖定比例（活動封面 16:9、頭像 1:1）。
 */

// 輸出寬度上限：太大只是讓上傳檔案變肥
const MAX_OUTPUT_WIDTH = 1600;
// 裁切框最小邊長（顯示座標）：再小難以操作，輸出解析度也過低
const MIN_CROP_SIZE = 60;
// 圖片顯示高度上限，避免直幅圖把整個頁面撐得很長
const MAX_DISPLAY_HEIGHT = "62vh";

const CORNERS = [
  { key: "nw", label: "左上" },
  { key: "ne", label: "右上" },
  { key: "sw", label: "左下" },
  { key: "se", label: "右下" },
];

export default function ImageCropper({
  file,
  // null＝自由比例
  aspectRatio = 16 / 9,
  aspectLabel = null,
  hint = null,
  confirmLabel = "套用裁切",
  loading = false,
  round = false,
  // allowOriginal：提供「直接使用原圖」，跳過裁切原封不動上傳
  // （使用者 2026-07-30：商品圖不一定要裁）
  allowOriginal = false,
  onCancel,
  onConfirm,
  onPickAnother,
}) {
  const [imageSrc, setImageSrc] = useState(null);
  const [natural, setNatural] = useState(null);
  const [display, setDisplay] = useState({ width: 0, height: 0 });
  const [crop, setCrop] = useState(null);

  const imageRef = useRef(null);
  const dragRef = useRef(null);
  const resizeRef = useRef(null);

  const isFree = aspectRatio === null;
  const ratioText = aspectLabel ?? (isFree ? "自由比例" : "");
  const hintText =
    hint ?? (isFree ? "拖曳框可移動，拖曳四角可改變範圍與比例" : "拖曳框可移動，拖曳四角可改變範圍");

  useEffect(() => {
    if (!file) {
      setImageSrc(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setImageSrc(url);
    setNatural(null);
    setCrop(null);
    // ObjectURL 必須釋放，否則換檔多次會累積佔用記憶體
    return () => URL.revokeObjectURL(url);
  }, [file]);

  /** 預設框：固定比例時在圖內最大化；自由比例時取整張圖。 */
  function defaultCrop(size) {
    if (!size.width || !size.height) return null;
    if (isFree) {
      return { x: 0, y: 0, width: size.width, height: size.height };
    }
    const width = Math.min(size.width, size.height * aspectRatio);
    const height = width / aspectRatio;
    return { x: (size.width - width) / 2, y: (size.height - height) / 2, width, height };
  }

  function measure() {
    const el = imageRef.current;
    if (!el || !el.clientWidth) return;
    const size = { width: el.clientWidth, height: el.clientHeight };
    setDisplay(size);
    setCrop(defaultCrop(size));
  }

  useEffect(() => {
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aspectRatio]);

  function handleImageLoad(event) {
    setNatural({
      width: event.target.naturalWidth,
      height: event.target.naturalHeight,
    });
    measure();
  }

  /** 把框夾在圖片內；固定比例時一律以寬度為主重算高度。 */
  function clampCrop(next) {
    if (!display.width) return next;

    let width = Math.max(MIN_CROP_SIZE, next.width);
    let height = Math.max(MIN_CROP_SIZE, next.height);

    if (!isFree) {
      width = Math.min(width, display.width, display.height * aspectRatio);
      height = width / aspectRatio;
    } else {
      width = Math.min(width, display.width);
      height = Math.min(height, display.height);
    }

    return {
      width,
      height,
      x: Math.min(Math.max(0, next.x), display.width - width),
      y: Math.min(Math.max(0, next.y), display.height - height),
    };
  }

  function handleBodyPointerDown(event) {
    if (!crop) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      origin: { ...crop },
    };
  }

  function handleBodyPointerMove(event) {
    const drag = dragRef.current;
    if (!drag) return;
    setCrop(
      clampCrop({
        ...drag.origin,
        x: drag.origin.x + (event.clientX - drag.startX),
        y: drag.origin.y + (event.clientY - drag.startY),
      }),
    );
  }

  function handleBodyPointerUp(event) {
    if (dragRef.current) {
      event.currentTarget.releasePointerCapture?.(event.pointerId);
      dragRef.current = null;
    }
  }

  function handleCornerPointerDown(event, corner) {
    // 不讓事件傳到框body，否則會同時觸發移動
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    resizeRef.current = {
      corner,
      startX: event.clientX,
      startY: event.clientY,
      origin: { ...crop },
    };
  }

  function handleCornerPointerMove(event) {
    const resize = resizeRef.current;
    if (!resize) return;
    event.stopPropagation();

    const dx = event.clientX - resize.startX;
    const dy = event.clientY - resize.startY;
    const o = resize.origin;
    // 對角是固定不動的那一角，據此算出新的框
    const right = o.x + o.width;
    const bottom = o.y + o.height;

    let next;
    switch (resize.corner) {
      case "nw":
        next = { x: o.x + dx, y: o.y + dy, width: o.width - dx, height: o.height - dy };
        break;
      case "ne":
        next = { x: o.x, y: o.y + dy, width: o.width + dx, height: o.height - dy };
        break;
      case "sw":
        next = { x: o.x + dx, y: o.y, width: o.width - dx, height: o.height + dy };
        break;
      default:
        next = { x: o.x, y: o.y, width: o.width + dx, height: o.height + dy };
    }

    if (!isFree) {
      // 鎖比例時以寬度為主，並讓固定的那一角維持不動
      const width = Math.max(MIN_CROP_SIZE, next.width);
      const height = width / aspectRatio;
      next = {
        width,
        height,
        x: resize.corner === "nw" || resize.corner === "sw" ? right - width : next.x,
        y: resize.corner === "nw" || resize.corner === "ne" ? bottom - height : next.y,
      };
    }

    setCrop(clampCrop(next));
  }

  function handleCornerPointerUp(event) {
    if (resizeRef.current) {
      event.stopPropagation();
      event.currentTarget.releasePointerCapture?.(event.pointerId);
      resizeRef.current = null;
    }
  }

  /** 滑桿：以框中心為錨點等比縮放目前的框（自由比例時維持當下的寬高比）。 */
  function handleSizeChange(percent) {
    if (!crop || !display.width) return;
    const maxWidth = isFree
      ? display.width
      : Math.min(display.width, display.height * aspectRatio);
    const currentRatio = crop.width / crop.height;
    const centerX = crop.x + crop.width / 2;
    const centerY = crop.y + crop.height / 2;

    let width = (maxWidth * percent) / 100;
    let height = isFree ? width / currentRatio : width / aspectRatio;
    // 自由比例下高度可能先撞到圖片上下緣，等比縮回去
    if (height > display.height) {
      height = display.height;
      width = height * currentRatio;
    }

    setCrop(clampCrop({ width, height, x: centerX - width / 2, y: centerY - height / 2 }));
  }

  function handleReset() {
    measure();
  }

  /** 把框的顯示座標換算回原圖座標，只輸出框內那一塊。 */
  async function handleConfirm() {
    if (!natural || !crop || !display.width) return;

    const k = natural.width / display.width;
    const sourceWidth = crop.width * k;
    const sourceHeight = crop.height * k;

    // 不放大：輸出最多就是實際裁到的像素數
    const outputWidth = Math.min(MAX_OUTPUT_WIDTH, Math.round(sourceWidth));
    const outputHeight = Math.round(outputWidth * (sourceHeight / sourceWidth));

    const canvas = document.createElement("canvas");
    canvas.width = outputWidth;
    canvas.height = outputHeight;
    const ctx = canvas.getContext("2d");

    const image = new Image();
    image.src = imageSrc;
    await image.decode();
    ctx.drawImage(
      image,
      crop.x * k,
      crop.y * k,
      sourceWidth,
      sourceHeight,
      0,
      0,
      outputWidth,
      outputHeight,
    );

    // 統一輸出 WebP：後端接受此格式，體積也比 PNG 小。
    // 副檔名要跟著換，否則後端的副檔名檢查會擋下來。
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/webp", 0.92));
    const baseName = (file?.name ?? "image").replace(/\.[^.]+$/, "");
    onConfirm(new File([blob], `${baseName}.webp`, { type: "image/webp" }));
  }

  if (!imageSrc) return null;

  const maxWidthForRatio = isFree
    ? display.width
    : Math.min(display.width, display.height * (aspectRatio || 1));
  const sizePercent =
    crop && maxWidthForRatio ? Math.round((crop.width / maxWidthForRatio) * 100) : 100;
  const outputSize =
    natural && crop && display.width
      ? {
          width: Math.round(crop.width * (natural.width / display.width)),
          height: Math.round(crop.height * (natural.width / display.width)),
        }
      : null;

  return (
    <div className={`cropper${round ? " is-round" : ""}`}>
      {/* 容器寬高由圖片決定，因此圖片永遠填滿它、不會有留白 */}
      <div className="cropper-stage">
        <img
          ref={imageRef}
          className="cropper-image"
          src={imageSrc}
          alt=""
          draggable={false}
          onLoad={handleImageLoad}
          style={{ maxHeight: MAX_DISPLAY_HEIGHT }}
        />

        {crop && (
          <div
            className="cropper-window"
            style={{
              left: `${crop.x}px`,
              top: `${crop.y}px`,
              width: `${crop.width}px`,
              height: `${crop.height}px`,
            }}
            onPointerDown={handleBodyPointerDown}
            onPointerMove={handleBodyPointerMove}
            onPointerUp={handleBodyPointerUp}
            onPointerCancel={handleBodyPointerUp}
          >
            {ratioText && <span className="cropper-ratio-tag">{ratioText}</span>}
            {CORNERS.map((corner) => (
              <span
                key={corner.key}
                className={`cropper-handle is-${corner.key}`}
                role="button"
                aria-label={`調整${corner.label}`}
                onPointerDown={(event) => handleCornerPointerDown(event, corner.key)}
                onPointerMove={handleCornerPointerMove}
                onPointerUp={handleCornerPointerUp}
                onPointerCancel={handleCornerPointerUp}
              />
            ))}
          </div>
        )}
      </div>

      <div className="cropper-toolbar">
        <span className="cropper-hint">{hintText}</span>

        <div className="cropper-zoom">
          <button
            type="button"
            className="cropper-zoom-btn"
            aria-label="縮小裁切範圍"
            onClick={() => handleSizeChange(Math.max(10, sizePercent - 10))}
          >
            −
          </button>
          <input
            type="range"
            min={10}
            max={100}
            step={1}
            value={Math.min(100, Math.max(10, sizePercent))}
            aria-label="裁切範圍大小"
            onChange={(event) => handleSizeChange(Number(event.target.value))}
          />
          <button
            type="button"
            className="cropper-zoom-btn"
            aria-label="放大裁切範圍"
            onClick={() => handleSizeChange(Math.min(100, sizePercent + 10))}
          >
            ＋
          </button>
          {outputSize && (
            <span className="cropper-zoom-value">
              {outputSize.width}×{outputSize.height}
            </span>
          )}
        </div>

        <div className="cropper-actions">
          <button type="button" className="cropper-text-btn" onClick={handleReset}>
            <RefreshIcon />
            重設
          </button>
          {onPickAnother && (
            <button type="button" className="cropper-text-btn" onClick={onPickAnother}>
              <UploadIcon />
              更換圖片
            </button>
          )}
        </div>
      </div>

      <div className="cropper-footer">
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            取消
          </Button>
        )}
        {/* 直接用原圖：原封不動送出，連格式與品質都不動
            （裁切會重新編碼，不裁就沒必要多壓一次） */}
        {allowOriginal && (
          <Button
            type="button"
            variant="secondary"
            loading={loading}
            onClick={() => onConfirm(file)}
          >
            直接使用原圖
          </Button>
        )}
        <Button type="button" loading={loading} onClick={handleConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </div>
  );
}
