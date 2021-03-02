const { API_PROTOCOL, API_HOST } = process.env;

export default class Endpoints {
    static baseUrl = `${API_PROTOCOL}://${API_HOST}`;

    static uploadUrl = `${API_PROTOCOL}://${API_HOST}/api​/v1​/data_extraction_tasks​/`;
}