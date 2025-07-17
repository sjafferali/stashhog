import React, { useState } from 'react';
import { Image, ImageProps } from 'antd';

interface SceneThumbnailProps extends Omit<ImageProps, 'src'> {
  sceneId: string;
  title?: string;
}

const PLACEHOLDER_IMAGE =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

export const SceneThumbnail: React.FC<SceneThumbnailProps> = ({
  sceneId,
  title = 'Scene thumbnail',
  ...imageProps
}) => {
  const [hasError, setHasError] = useState(false);
  const [src, setSrc] = useState<string | undefined>(undefined);

  React.useEffect(() => {
    // For now, we don't have thumbnails implemented, so we'll always use placeholder
    // When thumbnails are implemented, you can add logic here to check if thumbnail exists
    // For example, you could make a HEAD request to check if the thumbnail exists
    // or have a field in the Scene model indicating thumbnail availability

    // TODO: Implement thumbnail availability check when backend supports it
    const thumbnailsImplemented = false; // Change this when thumbnails are implemented

    if (thumbnailsImplemented && !hasError) {
      setSrc(`/api/scenes/${sceneId}/thumbnail`);
    } else {
      setSrc(PLACEHOLDER_IMAGE);
    }
  }, [sceneId, hasError]);

  return (
    <Image
      {...imageProps}
      alt={title}
      src={src || PLACEHOLDER_IMAGE}
      fallback={PLACEHOLDER_IMAGE}
      preview={false}
      onError={() => {
        setHasError(true);
        setSrc(PLACEHOLDER_IMAGE);
      }}
    />
  );
};
