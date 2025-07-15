import { Scene } from '@/types/models';

export const exportToJSON = (scenes: Scene[], filename: string) => {
  const dataStr = JSON.stringify(scenes, null, 2);
  const dataUri =
    'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);

  const exportFileDefaultName = `${filename}.json`;

  const linkElement = document.createElement('a');
  linkElement.setAttribute('href', dataUri);
  linkElement.setAttribute('download', exportFileDefaultName);
  linkElement.click();
};

export const exportToCSV = (scenes: Scene[], filename: string) => {
  const headers = [
    'ID',
    'Title',
    'Path',
    'Date',
    'Duration',
    'Size',
    'Resolution',
    'Codec',
    'Framerate',
    'Bitrate',
    'Tags',
  ];

  const rows = scenes.map((scene) => [
    scene.id,
    scene.title || '',
    scene.path,
    scene.date || '',
    scene.duration || '',
    scene.size || '',
    scene.resolution || '',
    scene.video_codec || '',
    scene.framerate || '',
    scene.bitrate || '',
    (scene.tags || []).map((tag) => tag.name).join(', '),
  ]);

  const csvContent = [
    headers.join(','),
    ...rows.map((row) =>
      row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')
    ),
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.csv`);
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
