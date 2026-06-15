import { useEffect, useState } from "react";

interface ImageThumbnailProps {
  src: string | null | undefined;
  alt?: string;
  className: string;
}

export function ImageThumbnail({ src, alt = "", className }: ImageThumbnailProps) {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setHasError(false);
  }, [src]);

  if (!src || hasError) {
    return <span className={`${className} image-placeholder`} aria-hidden="true" />;
  }

  return (
    <img
      className={className}
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setHasError(true)}
    />
  );
}
