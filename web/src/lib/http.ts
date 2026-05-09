import ky from "ky";

interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  msg: string;
}

export const api = ky.create({
  timeout: 30000,
  hooks: {
    afterResponse: [
      async ({ response }) => {
        const body: ApiResponse = await response.json();
        if (body.code === 500) {
          throw new Error(body.msg || "server error");
        }
        return new Response(JSON.stringify(body.data), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      },
    ],
  },
});
