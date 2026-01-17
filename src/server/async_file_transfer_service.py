import os
import base64
import asyncio

CHUNK_SIZE = 4096

class AsyncFileTransferService:
    def __init__(self, save_dir='received_files'):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    async def send_file(self, writer, filepath, receiver=None):
        """
        Gửi file qua asyncio StreamWriter, chia chunk, gửi bất đồng bộ.
        """
        import aiofiles
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        # Gửi thông tin file
        file_info = {
            'type': 'FILE_REQUEST',
            'payload': {
                'filename': filename,
                'filesize': filesize,
                'receiver': receiver
            }
        }
        await self._send_json(writer, file_info)
        # Gửi từng chunk
        chunk_num = 0
        async with aiofiles.open(filepath, 'rb') as f:
            while True:
                chunk = await f.read(CHUNK_SIZE)
                if not chunk:
                    break
                chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                chunk_msg = {
                    'type': 'FILE_CHUNK',
                    'payload': {
                        'chunk_num': chunk_num,
                        'data': chunk_b64
                    }
                }
                await self._send_json(writer, chunk_msg)
                chunk_num += 1
        # Gửi thông điệp kết thúc
        end_msg = {'type': 'FILE_END', 'payload': {}}
        await self._send_json(writer, end_msg)

    async def receive_file(self, reader):
        """
        Nhận file từ asyncio StreamReader, ghép chunk lại thành file hoàn chỉnh.
        """
        file_data = None
        while True:
            msg = await self._recv_json(reader)
            if not msg:
                break
            msg_type = msg.get('type')
            if msg_type == 'FILE_REQUEST':
                file_data = msg['payload']
                file_data['chunks'] = []
            elif msg_type == 'FILE_CHUNK':
                file_data['chunks'].append(msg['payload'])
            elif msg_type == 'FILE_END':
                self._save_file(file_data)
                break
        return file_data

    def _save_file(self, file_data):
        filename = file_data['filename']
        chunks = file_data['chunks']
        filepath = os.path.join(self.save_dir, filename)
        with open(filepath, 'wb') as f:
            for chunk in chunks:
                data = base64.b64decode(chunk['data'])
                f.write(data)
        print(f"[FILE] Đã nhận và lưu file: {filepath}")

    async def _send_json(self, writer, data):
        import json
        msg = json.dumps(data).encode('utf-8') + b'\n'
        writer.write(msg)
        await writer.drain()

    async def _recv_json(self, reader):
        import json
        line = await reader.readline()
        if not line:
            return None
        try:
            return json.loads(line.decode('utf-8'))
        except Exception:
            return None

# Ví dụ sử dụng với asyncio:
# import asyncio
# from async_file_transfer_service import AsyncFileTransferService
#
# async def main():
#     reader, writer = await asyncio.open_connection('localhost', 5555)
#     service = AsyncFileTransferService()
#     # Gửi file
#     await service.send_file(writer, 'path/to/file.txt')
#     # Nhận file
#     await service.receive_file(reader)
#     writer.close()
#     await writer.wait_closed()
#
# asyncio.run(main())
