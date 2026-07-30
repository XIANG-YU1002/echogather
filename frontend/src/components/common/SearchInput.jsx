import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { searchCharacters } from "../../api/search.js";
import { SearchIcon } from "./icons.jsx";

/** 建議清單一次最多顯示幾個角色 */
const SUGGEST_LIMIT = 8;
/** 邊打邊查的等待時間；太短會對每個字送一次請求 */
const DEBOUNCE_MS = 250;

export default function SearchInput({ className = "" }) {
  const [value, setValue] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  // 角色名稱建議：讓使用者先確認是不是自己要找的角色，選了就直接看該角色的商品
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  // -1＝停在輸入框（Enter 是一般全站搜尋）；0 起算對應建議項
  const [activeIndex, setActiveIndex] = useState(-1);
  const formRef = useRef(null);
  // 每次查詢的序號，只有最後一次的結果可以進 state（避免慢的舊請求覆蓋新結果）
  const requestSeq = useRef(0);

  useEffect(() => {
    if (location.pathname === "/search") {
      setValue(searchParams.get("q") ?? "");
    } else {
      setValue("");
    }
    setOpen(false);
    setActiveIndex(-1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname, searchParams]);

  useEffect(() => {
    const keyword = value.trim();
    if (!keyword) {
      setSuggestions([]);
      setOpen(false);
      return undefined;
    }

    const seq = ++requestSeq.current;
    const timer = setTimeout(() => {
      searchCharacters(keyword, { pageSize: SUGGEST_LIMIT })
        .then((response) => {
          if (seq !== requestSeq.current) return;
          setSuggestions(response.data);
          setActiveIndex(-1);
          setOpen(true);
        })
        .catch(() => {
          // 建議查不到就不顯示，不要用錯誤訊息打斷輸入
          if (seq !== requestSeq.current) return;
          setSuggestions([]);
          setOpen(false);
        });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [value]);

  // 點到搜尋框以外就收起來
  useEffect(() => {
    function handlePointerDown(event) {
      if (formRef.current && !formRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  function goKeywordSearch() {
    const trimmed = value.trim();
    if (!trimmed) return;
    setOpen(false);
    navigate(`/search?q=${encodeURIComponent(trimmed)}`);
  }

  /** 選了角色就直接看該角色的商品（與搜尋結果頁的角色卡片同一個目的地） */
  function goCharacterSearch(character) {
    setOpen(false);
    setValue(character.name);
    navigate(
      `/search?character_id=${character.id}&name=${encodeURIComponent(character.name)}`,
    );
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (activeIndex >= 0 && suggestions[activeIndex]) {
      goCharacterSearch(suggestions[activeIndex]);
      return;
    }
    goKeywordSearch();
  }

  function handleKeyDown(event) {
    if (event.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
      return;
    }
    if (!open || suggestions.length === 0) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((prev) => (prev + 1 >= suggestions.length ? -1 : prev + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((prev) => (prev - 1 < -1 ? suggestions.length - 1 : prev - 1));
    }
  }

  const showSuggestions = open && suggestions.length > 0;

  return (
    <form
      ref={formRef}
      className={`search-input ${className}`}
      onSubmit={handleSubmit}
      role="search"
    >
      <input
        type="search"
        placeholder="搜尋商品或角色"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        aria-label="全站搜尋"
        aria-expanded={showSuggestions}
        aria-controls="search-suggest-list"
        autoComplete="off"
      />
      <button type="submit" className="search-input-icon-btn" aria-label="搜尋">
        <SearchIcon className="icon-search" />
      </button>

      {showSuggestions && (
        <div className="search-suggest" id="search-suggest-list" role="listbox">
          <button
            type="button"
            className={`search-suggest-item is-keyword${activeIndex === -1 ? " is-active" : ""}`}
            onClick={goKeywordSearch}
            onMouseEnter={() => setActiveIndex(-1)}
          >
            <SearchIcon />
            <span className="search-suggest-name">搜尋「{value.trim()}」</span>
          </button>

          <div className="search-suggest-group">角色</div>
          {suggestions.map((character, index) => (
            <button
              key={character.id}
              type="button"
              role="option"
              aria-selected={activeIndex === index}
              className={`search-suggest-item${activeIndex === index ? " is-active" : ""}`}
              onClick={() => goCharacterSearch(character)}
              onMouseEnter={() => setActiveIndex(index)}
            >
              <span className="search-suggest-name">{character.name}</span>
              <span className="search-suggest-count">
                關聯商品 {character.related_product_count} 件
              </span>
            </button>
          ))}
        </div>
      )}
    </form>
  );
}
